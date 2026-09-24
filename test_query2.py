import os, sys
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.chdir(r"d:\code_item\酒馆rag")

import chromadb, torch
from transformers import AutoModel, AutoTokenizer

c = chromadb.PersistentClient(path=r"RAG\chroma_db")
col = c.get_collection("sillytavern_docs")
print("count:", col.count())

tk = AutoTokenizer.from_pretrained("BAAI/bge-large-zh-v1.5", local_files_only=True)
m = AutoModel.from_pretrained("BAAI/bge-large-zh-v1.5", local_files_only=True).to("cpu")
m.eval()

q = "如何用正则替换文字"
inp = tk([q], padding=True, truncation=True, max_length=512, return_tensors="pt")
with torch.no_grad():
    out = m(**inp)
    emb = out.last_hidden_state[:, 0]
    emb = torch.nn.functional.normalize(emb, p=2, dim=1)
qe = emb.numpy().tolist()

print("Testing query...")
r = col.query(query_embeddings=qe, n_results=3, include=["documents","metadatas"])
print("query OK:", len(r["ids"][0]), "results")

print("Testing get...")
try:
    all_data = col.get(limit=10, include=["documents"])
    print("get OK:", len(all_data["ids"]), "results")
except Exception as e:
    print("get FAILED:", e)
