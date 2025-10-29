import json
from statistics import mean
import matplotlib.pyplot as plt

with open('/Users/Tienbruse/tmdt/Backend/company-llm/test/result.json', 'r', encoding='utf-8') as f:
    data_json = json.load(f)

rag_metrics = {
    'rouge1': [],
    'rouge2': [],
    'rougeL': [],
    'meteor': [],
    'bertscore': [],
    'deepseek_score': []
}

deepseek_metrics = {
    'rouge1': [],
    'rouge2': [],
    'rougeL': [],
    'meteor': [],
    'bertscore': [],
    'deepseek_score': []
}

for item in data_json:
    rag = item.get('RAG', {})
    rag_metrics['rouge1'].append(rag.get('rouge1', 0))
    rag_metrics['rouge2'].append(rag.get('rouge2', 0))
    rag_metrics['rougeL'].append(rag.get('rougeL', 0))
    rag_metrics['meteor'].append(rag.get('meteor', 0))
    rag_metrics['bertscore'].append(rag.get('bertscore', 0))
    rag_metrics['deepseek_score'].append(rag.get('deepseek_score', 0))

    deepseek = item.get('Deepseek', {})
    deepseek_metrics['rouge1'].append(deepseek.get('rouge1', 0))
    deepseek_metrics['rouge2'].append(deepseek.get('rouge2', 0))
    deepseek_metrics['rougeL'].append(deepseek.get('rougeL', 0))
    deepseek_metrics['meteor'].append(deepseek.get('meteor', 0))
    deepseek_metrics['bertscore'].append(deepseek.get('bertscore', 0))
    deepseek_metrics['deepseek_score'].append(deepseek.get('deepseek_score', 0))

def calculate_average(metrics):
    return {key: round(mean(values), 4) for key, values in metrics.items()}

rag_averages = calculate_average(rag_metrics)
deepseek_averages = calculate_average(deepseek_metrics)

rag_averages['bertscore'] *= 100 
rag_averages['deepseek_score'] /= 10  
deepseek_averages['bertscore'] *= 100  
deepseek_averages['deepseek_score'] /= 10  

metrics = ['rouge1', 'rouge2', 'rougeL', 'meteor', 'bertscore', 'deepseek_score']

rag_values = [rag_averages[m] for m in metrics]
deepseek_values = [deepseek_averages[m] for m in metrics]

x = range(len(metrics))  
width = 0.35 

fig, ax = plt.subplots(figsize=(10, 6))
ax.bar([i - width/2 for i in x], rag_values, width, label='RAG', color='skyblue')
ax.bar([i + width/2 for i in x], deepseek_values, width, label='Deepseek', color='salmon')

ax.set_xlabel('Chỉ số')
ax.set_ylabel('Giá trị')
ax.set_title('Đánh giá Deepseek RAG và Deepseek')
ax.set_xticks(x)
ax.set_xticklabels(metrics, rotation=45)
ax.legend()

for i, v in enumerate(rag_values):
    ax.text(i - width/2, v + 0.01, f'{v:.4f}', ha='center', va='bottom')
for i, v in enumerate(deepseek_values):
    ax.text(i + width/2, v + 0.01, f'{v:.4f}', ha='center', va='bottom')

plt.tight_layout()
plt.show()

print("Trung bình các chỉ số cho RAG:")
for metric, value in rag_averages.items():
    print(f"{metric}: {value}")

print("\nTrung bình các chỉ số cho Deepseek:")
for metric, value in deepseek_averages.items():
    print(f"{metric}: {value}")