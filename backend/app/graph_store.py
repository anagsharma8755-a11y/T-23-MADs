from collections import defaultdict
from datetime import datetime
from neo4j import GraphDatabase
from .config import settings

class Neo4jGraphStore:
    """Dataset-scoped property graph. Relational storage remains the source of truth."""
    def __init__(self):
        self.driver = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_username, settings.neo4j_password)) if settings.neo4j_enabled else None

    @property
    def enabled(self): return self.driver is not None

    def verify(self):
        if not self.driver: return False
        self.driver.verify_connectivity(); return True

    def ensure_schema(self):
        if not self.driver: return
        self.driver.execute_query("CREATE CONSTRAINT account_dataset_key IF NOT EXISTS FOR (a:Account) REQUIRE a.key IS UNIQUE")
        self.driver.execute_query("CREATE INDEX transfer_dataset IF NOT EXISTS FOR ()-[t:TRANSFER]-() ON (t.dataset_id)")

    def sync_dataset(self, dataset_id:int, workspace_id:int, accounts, transactions):
        if not self.driver: return
        self.ensure_schema()
        account_rows=[{"key":f"{dataset_id}:{a.account_id}","account_id":a.account_id,"dataset_id":dataset_id,"workspace_id":workspace_id,"created_at":a.created_at.isoformat() if a.created_at else None,"device_id":a.device_id,"ip_address":a.ip_address,"kyc_group_id":a.kyc_group_id} for a in accounts]
        tx_rows=[{"id":t.transaction_id,"dataset_id":dataset_id,"workspace_id":workspace_id,"sender_key":f"{dataset_id}:{t.sender_account}","receiver_key":f"{dataset_id}:{t.receiver_account}","amount":float(t.amount),"currency":t.currency,"timestamp":t.timestamp.isoformat()} for t in transactions]
        with self.driver.session() as session:
            session.run("MATCH (a:Account {dataset_id:$dataset_id}) DETACH DELETE a",dataset_id=dataset_id).consume()
            for start in range(0,len(account_rows),1000):
                session.run("UNWIND $rows AS row MERGE (a:Account {key:row.key}) SET a += row",rows=account_rows[start:start+1000]).consume()
            for start in range(0,len(tx_rows),1000):
                session.run("UNWIND $rows AS row MATCH (s:Account {key:row.sender_key}),(r:Account {key:row.receiver_key}) CREATE (s)-[t:TRANSFER]->(r) SET t = row",rows=tx_rows[start:start+1000]).consume()

    def neighborhood(self,dataset_id:int,account_id:str,hops:int,node_limit:int,edge_limit:int,start:str|None=None,end:str|None=None):
        if not self.driver: return None
        depth=1 if hops<=1 else 2
        query=f"""MATCH (root:Account {{dataset_id:$dataset_id,account_id:$account_id}})
        MATCH p=(root)-[rels:TRANSFER*1..{depth}]-(other:Account)
        WHERE all(rel IN rels WHERE rel.dataset_id=$dataset_id
          AND ($start IS NULL OR datetime(rel.timestamp)>=datetime($start))
          AND ($end IS NULL OR datetime(rel.timestamp)<=datetime($end)))
        RETURN p LIMIT $path_limit"""
        records,_,_=self.driver.execute_query(query,dataset_id=dataset_id,account_id=account_id,start=start,end=end,path_limit=edge_limit*2)
        nodes={account_id:{"id":account_id}}; edges={}; truncated=False
        for rec in records:
            path=rec["p"]
            for node in path.nodes:
                aid=node.get("account_id")
                if aid not in nodes and len(nodes)>=node_limit: truncated=True; continue
                nodes[aid]={"id":aid}
            for rel in path.relationships:
                tid=rel.get("id")
                if tid in edges: continue
                if len(edges)>=edge_limit: truncated=True; continue
                sender=rel.start_node.get("account_id"); receiver=rel.end_node.get("account_id")
                if sender in nodes and receiver in nodes:
                    edges[tid]={"transaction_id":tid,"source":sender,"target":receiver,"currency":rel.get("currency"),"amount":float(rel.get("amount")),"timestamp":rel.get("timestamp")}
        grouped={}
        for t in edges.values():
            k=(t["source"],t["target"],t["currency"]); g=grouped.setdefault(k,{"source":k[0],"target":k[1],"currency":k[2],"count":0,"total":0,"transactions":[]}); g["count"]+=1; g["total"]+=t["amount"]; g["transactions"].append({"id":t["transaction_id"],"amount":t["amount"],"timestamp":t["timestamp"]})
        return {"nodes":list(nodes.values()),"edges":list(grouped.values()),"truncated":truncated,"source":"neo4j"}

    def sync_blockchain_dataset(self,dataset_id:int,workspace_id:int,wallets,transactions,relationships):
        """Mirror typed Elliptic++ nodes/edges without flattening transaction structure."""
        if not self.driver: return
        self.driver.execute_query("CREATE CONSTRAINT wallet_dataset_key IF NOT EXISTS FOR (n:EllipticWallet) REQUIRE n.key IS UNIQUE")
        self.driver.execute_query("CREATE CONSTRAINT bitcoin_tx_dataset_key IF NOT EXISTS FOR (n:BitcoinTransaction) REQUIRE n.key IS UNIQUE")
        wallet_rows=[{"key":f"elliptic:{dataset_id}:wallet:{x.address}","node_id":x.address,"node_type":"wallet","dataset_id":dataset_id,"workspace_id":workspace_id,"time_step":x.time_step} for x in wallets]
        tx_rows=[{"key":f"elliptic:{dataset_id}:transaction:{x.tx_id}","node_id":x.tx_id,"node_type":"transaction","dataset_id":dataset_id,"workspace_id":workspace_id,"time_step":x.time_step} for x in transactions]
        with self.driver.session() as session:
            session.run("MATCH (n) WHERE (n:EllipticWallet OR n:BitcoinTransaction) AND n.dataset_id=$dataset_id DETACH DELETE n",dataset_id=dataset_id).consume()
            for start in range(0,len(wallet_rows),1000): session.run("UNWIND $rows AS row MERGE (n:EllipticWallet {key:row.key}) SET n += row",rows=wallet_rows[start:start+1000]).consume()
            for start in range(0,len(tx_rows),1000): session.run("UNWIND $rows AS row MERGE (n:BitcoinTransaction {key:row.key}) SET n += row",rows=tx_rows[start:start+1000]).consume()
            for relationship_type in ("ADDR_ADDR","ADDR_TX","TX_ADDR","TX_TX"):
                rows=[{"source_key":f"elliptic:{dataset_id}:{x.source_type}:{x.source_id}","target_key":f"elliptic:{dataset_id}:{x.target_type}:{x.target_id}","dataset_id":dataset_id} for x in relationships if x.relationship_type==relationship_type]
                query=f"UNWIND $rows AS row MATCH (s {{key:row.source_key}}),(t {{key:row.target_key}}) CREATE (s)-[r:{relationship_type}]->(t) SET r.dataset_id=row.dataset_id"
                for start in range(0,len(rows),1000): session.run(query,rows=rows[start:start+1000]).consume()

    def blockchain_neighborhood(self,dataset_id:int,wallet_id:str,hops:int,node_limit:int,edge_limit:int):
        if not self.driver: return None
        depth=min(max(hops,1),3)
        query=f"""MATCH (root:EllipticWallet {{dataset_id:$dataset_id,node_id:$wallet_id}})
        MATCH p=(root)-[*1..{depth}]-(other)
        WHERE all(n IN nodes(p) WHERE n.dataset_id=$dataset_id)
        RETURN p LIMIT $path_limit"""
        records,_,_=self.driver.execute_query(query,dataset_id=dataset_id,wallet_id=wallet_id,path_limit=edge_limit*2)
        nodes={}; edges={}; truncated=False
        for record in records:
            path=record["p"]
            for node in path.nodes:
                key=(node.get("node_type"),node.get("node_id"))
                if key not in nodes and len(nodes)>=node_limit: truncated=True; continue
                nodes[key]={"id":key[1],"node_type":key[0],"time_step":node.get("time_step")}
            for rel in path.relationships:
                source=(rel.start_node.get("node_type"),rel.start_node.get("node_id")); target=(rel.end_node.get("node_type"),rel.end_node.get("node_id")); key=(rel.type,source,target)
                if key in edges: continue
                if len(edges)>=edge_limit: truncated=True; continue
                if source in nodes and target in nodes: edges[key]={"id":f"neo4j-{len(edges)}","source":source[1],"target":target[1],"source_type":source[0],"target_type":target[0],"relationship_type":rel.type}
        return {"nodes":list(nodes.values()),"edges":list(edges.values()),"truncated":truncated,"source":"neo4j"}

graph_store=Neo4jGraphStore()
