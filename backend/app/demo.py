import csv, io
from datetime import datetime, timedelta, timezone

def demo_csvs():
    base=datetime(2026,1,15,9,0,tzinfo=timezone.utc); tx=[]
    def add(i,m,s,r,a,c="INR"): tx.append([i,(base+timedelta(minutes=m)).isoformat(),s,r,str(a),c,"","","",""])
    # Ordinary, boundary and legitimate activity.
    add("ORD-001",0,"01001","01002",1200); add("ORD-002",90,"01002","01003",350); add("BOUND-001",0,"09001","09002",1000,"USD"); add("BOUND-002",25,"09002","09003",900,"USD")
    # Fan-in/fan-out.
    for i,(s,a) in enumerate([("11001",12000),("11002",14000),("11003",10000),("11004",12000)]): add(f"FAN-IN-{i+1}",10+i,s,"00100",a)
    add("FAN-OUT-1",16,"00100","12001",23000); add("FAN-OUT-2",17,"00100","12002",22000)
    # Chronological cycle.
    add("CYCLE-1",30,"00200","00201",9000); add("CYCLE-2",34,"00201","00202",8700); add("CYCLE-3",39,"00202","00200",8400)
    # Four-account chain.
    add("CHAIN-1",50,"00300","00301",7000); add("CHAIN-2",54,"00301","00302",6800); add("CHAIN-3",58,"00302","00303",6500)
    # Same values in another currency must stay separate.
    add("FX-1",12,"11001","00100",500,"USD"); add("FX-2",14,"00100","12001",450,"USD")
    out=io.StringIO(); w=csv.writer(out,lineterminator="\n"); w.writerow(["transaction_id","timestamp","sender_account","receiver_account","amount","currency","sender_device_id","receiver_device_id","sender_ip","receiver_ip"]); w.writerows(tx)
    accounts=[]
    all_ids=sorted({r[2] for r in tx}|{r[3] for r in tx})
    for account in all_ids: accounts.append([account,(base-timedelta(days=180)).isoformat(),"1000","",f"10.0.0.{int(account[-2:])%250+1}",""])
    for i in range(4): accounts.append([f"0040{i}",(base-timedelta(days=5-i)).isoformat(),"100","DEV-SHARED-7","172.16.1.50","KYC-SYN-42"])
    # Legitimate shared IP but old accounts; should not trigger recent-account detector.
    for i in range(3): accounts.append([f"0050{i}",(base-timedelta(days=400+i)).isoformat(),"500","", "192.168.1.10",""])
    ao=io.StringIO(); w=csv.writer(ao,lineterminator="\n"); w.writerow(["account_id","created_at","opening_balance","device_id","ip_address","kyc_group_id"]); w.writerows(accounts)
    labels={"rapid_fan":["00100"],"circular":["00200","00201","00202"],"pass_through":["00300","00301","00302","00303"],"shared_attribute":["00400","00401","00402","00403"]}
    return out.getvalue().encode(),ao.getvalue().encode(),labels

