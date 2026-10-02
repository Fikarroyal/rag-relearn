"""Fine-tuning cross-encoder dengan Hugging Face Transformers + PEFT/LoRA (opsional).
Jalankan: pip install -r ml/requirements-train.txt lalu `python -m ml.training.hf_lora_trainer datasets/train.jsonl`.
Tidak terikat GPU: otomatis memakai CPU bila CUDA tidak tersedia."""

from __future__ import annotations
import json
import sys


def train_lora(jsonl_path: str, base_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2", epochs=1, lr=2e-4, batch_size=8,
               max_len=256, lora_r=8, lora_alpha=16, out_dir="models/lora-reranker", corpus: dict | None = None):
    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(base_model)
    model = AutoModelForSequenceClassification.from_pretrained(base_model, num_labels=1)
    model = get_peft_model(model, LoraConfig(r=lora_r, lora_alpha=lora_alpha, target_modules=["query", "value"], lora_dropout=0.05, task_type="SEQ_CLS")).to(device)
    rows = [json.loads(l) for l in open(jsonl_path, encoding="utf-8")]
    text = lambda cid: (corpus or {}).get(cid, cid)
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=lr)
    for ep in range(epochs):
        for i in range(0, len(rows), batch_size):
            b = rows[i:i + batch_size]
            enc = lambda docs: tok([r["query"] for r in b], [text(d) for d in docs], truncation=True, max_length=max_len, padding=True, return_tensors="pt").to(device)
            pos, neg = model(**enc([r["positive"] for r in b])).logits.squeeze(-1), model(**enc([r["hard_negative"] for r in b])).logits.squeeze(-1)
            loss = torch.nn.functional.softplus(neg - pos).mean()  # pairwise logistic
            loss.backward(); opt.step(); opt.zero_grad()
            print(f"epoch={ep + 1} step={i // batch_size} loss={loss.item():.4f}")
    model.save_pretrained(out_dir); tok.save_pretrained(out_dir)
    return out_dir


if __name__ == "__main__":
    train_lora(sys.argv[1])
