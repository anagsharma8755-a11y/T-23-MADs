from collections import defaultdict
from datetime import timedelta, timezone
from decimal import Decimal
import hashlib, json
import networkx as nx

DEFAULTS={"fan_window_minutes":15,"fan_min_senders":3,"fan_min_receivers":2,"fan_share":0.8,"cycle_window_hours":24,"cycle_max_length":5,"chain_window_minutes":20,"chain_min_share":0.8,"new_account_days":30,"shared_min_accounts":3}
CAPS={"rapid_fan":40,"circular":35,"pass_through":35,"shared_attribute":15}
def fprint(d): return hashlib.sha256(json.dumps(d,sort_keys=True,default=str).encode()).hexdigest()
def finding(detector,accounts,txs,currency,evidence,reason,limits,contribution):
    base={"detector":detector,"detector_version":"1.0","account_ids":sorted(set(accounts)),"transaction_ids":list(dict.fromkeys(txs)),"currency":currency,"evidence":evidence,"reason":reason,"limitations":limits,"contribution":contribution}
    base["fingerprint"]=fprint({k:base[k] for k in ("detector","account_ids","transaction_ids","currency","evidence")}); return base

def _dt(v):
    return v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v
def analyze(txs,accounts,config=None):
    c={**DEFAULTS,**(config or {})}; out=[]; by_currency=defaultdict(list)
    for t in txs: by_currency[t.currency].append(t)
    for cur,items in by_currency.items():
        items.sort(key=lambda x:(_dt(x.timestamp),x.transaction_id)); incoming=defaultdict(list); outgoing=defaultdict(list)
        for t in items: incoming[t.receiver_account].append(t); outgoing[t.sender_account].append(t)
        graph=nx.DiGraph(); graph.add_edges_from((t.sender_account,t.receiver_account) for t in items)
        cyclic_nodes={n for component in nx.strongly_connected_components(graph) if len(component)>1 for n in component}
        # FIFO allocation: each incoming amount can fund later outgoing transfers once only.
        for acct,ins in incoming.items():
            for start_i,first in enumerate(ins):
                window_end=_dt(first.timestamp)+timedelta(minutes=c["fan_window_minutes"]); batch=[x for x in ins[start_i:] if _dt(x.timestamp)<=window_end]
                senders={x.sender_account for x in batch}; total=sum(Decimal(x.amount) for x in batch)
                outs=[x for x in outgoing.get(acct,[]) if _dt(first.timestamp)<=_dt(x.timestamp)<=window_end]
                available=total; used=[]; forwarded=Decimal(0)
                for x in outs:
                    take=min(available,Decimal(x.amount));
                    if take>0: forwarded+=take; used.append(x); available-=take
                    if available<=0: break
                share=float(forwarded/total) if total else 0
                receivers={x.receiver_account for x in used}
                if len(senders)>=c["fan_min_senders"] and len(receivers)>=c["fan_min_receivers"] and share>=c["fan_share"]:
                    txids=[x.transaction_id for x in batch]+[x.transaction_id for x in used]
                    reason=f"{acct} received {cur} {float(total):,.2f} from {len(senders)} accounts and forwarded {cur} {float(forwarded):,.2f} to {len(receivers)} accounts within {c['fan_window_minutes']} minutes."
                    out.append(finding("rapid_fan",[acct,*senders,*receivers],txids,cur,{"received":float(total),"forwarded":float(forwarded),"share":round(share,4),"distinct_senders":len(senders),"distinct_receivers":len(receivers),"window_minutes":c["fan_window_minutes"],"allocation":"FIFO, each incoming unit allocated at most once"},reason,["Transfer coverage may be incomplete; this indicates rapid pass-through activity, not a true account balance."],min(CAPS["rapid_fan"],20+len(senders)*2+len(receivers)*2))); break
        # Chronological bounded cycles via DFS over transaction edges.
        adj=defaultdict(list)
        for t in items: adj[t.sender_account].append(t)
        seen_cycles=set(); work=0
        for first in items:
            if first.sender_account not in cyclic_nodes: continue
            stack=[(first.receiver_account,[first.sender_account,first.receiver_account],[first],_dt(first.timestamp))]
            while stack and work<50000:
                node,path,path_txs,started=stack.pop(); work+=1
                if len(path)>c["cycle_max_length"]+1: continue
                for nxt in adj.get(node,[]):
                    if _dt(nxt.timestamp)<_dt(path_txs[-1].timestamp) or _dt(nxt.timestamp)-started>timedelta(hours=c["cycle_window_hours"]): continue
                    if nxt.receiver_account==path[0] and len(path)>=3:
                        ids=tuple(x.transaction_id for x in path_txs+[nxt]); key=tuple(sorted(ids))
                        if key not in seen_cycles:
                            seen_cycles.add(key); accts=path; hours=(_dt(nxt.timestamp)-started).total_seconds()/3600
                            out.append(finding("circular",accts,list(ids),cur,{"cycle_length":len(path),"elapsed_hours":round(hours,3),"max_cycle_length":c["cycle_max_length"],"window_hours":c["cycle_window_hours"]},f"Funds moved through a chronological {len(path)}-account cycle in {hours:.1f} hours and returned to {path[0]}.",["Amounts may differ between cycle legs; the finding proves chronological movement, not identical-fund tracing."],CAPS["circular"]))
                    elif nxt.receiver_account not in path: stack.append((nxt.receiver_account,path+[nxt.receiver_account],path_txs+[nxt],started))
        # Pass-through chains using chronological DFS and non-reused capacity per leg.
        seen_chain=set()
        for first in items:
            stack=[([first.sender_account,first.receiver_account],[first],Decimal(first.amount))]
            while stack:
                path,pts,capacity=stack.pop(); last=pts[-1]
                if 3<=len(path)<=6:
                    key=tuple(x.transaction_id for x in pts)
                    if key not in seen_chain:
                        seen_chain.add(key); share=min(1.0,min(float(Decimal(x.amount)/Decimal(pts[i-1].amount)) for i,x in enumerate(pts[1:],1))) if len(pts)>1 else 1
                        if share>=c["chain_min_share"]:
                            elapsed=(_dt(last.timestamp)-_dt(first.timestamp)).total_seconds()/60
                            out.append(finding("pass_through",path,list(key),cur,{"chain_length":len(path),"minimum_forward_share":round(share,4),"elapsed_minutes":round(elapsed,2),"allocation":"Each leg capped by the immediately preceding leg"},f"{len(path)} accounts formed a rapid pass-through chain over {elapsed:.1f} minutes, forwarding at least {share:.0%} at each step.",["This describes imported transfers only and is not a complete balance estimate."],min(CAPS["pass_through"],15+len(path)*4)))
                if len(path)>=6: continue
                for nxt in adj.get(path[-1],[]):
                    if nxt.receiver_account in path or _dt(nxt.timestamp)<_dt(last.timestamp) or _dt(nxt.timestamp)-_dt(last.timestamp)>timedelta(minutes=c["chain_window_minutes"]): continue
                    if Decimal(nxt.amount)>=capacity*Decimal(str(c["chain_min_share"])): stack.append((path+[nxt.receiver_account],pts+[nxt],min(capacity,Decimal(nxt.amount))))
    # Shared attributes only for known recently-created accounts.
    dated=[a for a in accounts if a.created_at]
    if dated:
        latest=max(_dt(a.created_at) for a in dated); cutoff=latest-timedelta(days=c["new_account_days"])
        for field,label in [("device_id","device"),("ip_address","IP address"),("kyc_group_id","synthetic KYC group")]:
            groups=defaultdict(list)
            for a in dated:
                value=getattr(a,field,None)
                if value and _dt(a.created_at)>=cutoff: groups[value].append(a.account_id)
            for value,ids in groups.items():
                if len(ids)>=c["shared_min_accounts"]:
                    out.append(finding("shared_attribute",ids,[],None,{"attribute_type":field,"attribute_value":value,"account_count":len(ids),"new_account_days":c["new_account_days"]},f"{len(ids)} recently created accounts share the same {label} ({value}).",["Shared attributes can be legitimate; this detector has a deliberately limited score contribution."],min(CAPS["shared_attribute"],5+len(ids)*2)))
    return out

def score_findings(findings):
    per=defaultdict(lambda:defaultdict(int)); ids=defaultdict(list)
    for idx,f in enumerate(findings):
        for account in f["account_ids"]:
            per[account][f["detector"]]=max(per[account][f["detector"]],f["contribution"]); ids[account].append(idx)
    result={}
    for acct,parts in per.items():
        bounded={k:min(v,CAPS[k]) for k,v in parts.items()}; score=min(100,sum(bounded.values())); severity="High" if score>=60 else "Medium" if score>=30 else "Low"
        result[acct]={"score":score,"severity":severity,"breakdown":bounded,"finding_indexes":ids[acct]}
    return result
