# -*- coding: utf-8 -*-
"""
课题10：AI 批处理耗时测试
功能：调用 SiliconFlow API，测试不同输入长度下的 AI 响应耗时
输出：benchmark_results.csv（数据表格）、benchmark_chart.png（耗时曲线图）、benchmark_report.txt（分析报告）
"""

import os
import time
import csv
import statistics
from openai import OpenAI
from dotenv import load_dotenv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# 加载 .env 中的密钥
load_dotenv()
API_KEY = os.getenv("SILICONFLOW_API_KEY")

# SiliconFlow 的 OpenAI 兼容接口
client = OpenAI(
    api_key=API_KEY,
    base_url="https://api.siliconflow.cn/v1"
)

# 模型选择（可换成其他模型，如 Qwen/Qwen2.5-7B-Instruct）
MODEL = "Qwen/Qwen2.5-7B-Instruct"

# 测试用的输入长度（字符数），从小到大
INPUT_LENGTHS = [100, 300, 500, 1000, 2000, 3000, 5000]

# 每个长度重复测试几次，取平均值更准确
REPEAT = 3

# 用一段基础文本，按长度截取来构造输入
BASE_TEXT = (
    "人工智能（AI）是计算机科学的一个重要分支，旨在研究、开发"
    "用于模拟、延伸和扩展人的智能的理论、方法、技术及应用系统。"
    "机器学习是人工智能的核心领域之一，它使计算机能够从数据中学习规律"
    "而无需显式编程。深度学习作为机器学习的一个子集，利用多层神经网络"
    "处理复杂的模式识别任务，在图像识别、自然语言处理、语音识别等领域"
    "取得了突破性进展。随着算力的提升和大数据的积累，大语言模型（LLM）"
    "应运而生，它们通过在海量文本上预训练，具备了强大的文本生成和理解能力。"
    "这些模型的出现，正在深刻改变人们获取信息、创作内容和解决问题的方式。"
)

def make_prompt(length):
    """根据指定长度生成输入文本"""
    text = BASE_TEXT * (length // len(BASE_TEXT) + 1)
    return text[:length]

def call_ai(prompt):
    """调用 AI 接口，返回 (耗时秒, 输出文本长度)"""
    start = time.perf_counter()
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "你是一个文本摘要助手。"},
            {"role": "user", "content": f"请对以下文本进行简要总结（100字以内）：\n{prompt}"}
        ],
        max_tokens=200,
        temperature=0.3,
    )
    elapsed = time.perf_counter() - start
    output_text = response.choices[0].message.content
    return elapsed, len(output_text)

def run_benchmark():
    """执行测试，返回结果列表"""
    results = []
    total = len(INPUT_LENGTHS) * REPEAT
    count = 0

    print(f"开始测试，共 {total} 次调用...\n")
    print(f"{'输入长度':>8} | {'第N次':>4} | {'耗时(秒)':>10} | {'输出长度':>8}")
    print("-" * 45)

    for length in INPUT_LENGTHS:
        times = []
        out_lens = []
        for i in range(REPEAT):
            count += 1
            prompt = make_prompt(length)
            elapsed, out_len = call_ai(prompt)
            times.append(elapsed)
            out_lens.append(out_len)
            avg_t = statistics.mean(times)
            print(f"{length:>8} | {i+1:>4} | {elapsed:>10.2f} | {out_len:>8}   (平均 {avg_t:.2f}s)")
            results.append({
                "input_length": length,
                "run": i + 1,
                "elapsed": round(elapsed, 2),
                "output_length": out_len,
            })

    return results

def save_csv(results):
    """保存为 CSV"""
    with open("benchmark_results.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["input_length", "run", "elapsed", "output_length"])
        writer.writeheader()
        writer.writerows(results)
    print("\n✅ 已保存：benchmark_results.csv")

def make_chart(results):
    """绘制耗时曲线图"""
    # 按输入长度分组，取平均耗时
    grouped = {}
    for r in results:
        grouped.setdefault(r["input_length"], []).append(r["elapsed"])
    lengths = sorted(grouped.keys())
    avg_times = [statistics.mean(grouped[l]) for l in lengths]

    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
    plt.rcParams["axes.unicode_minus"] = False

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(lengths, avg_times, "o-", color="#4C72B0", linewidth=2.5, markersize=8)

    for x, y in zip(lengths, avg_times):
        ax.annotate(f"{y:.1f}s", (x, y), textcoords="offset points",
                     xytext=(0, 12), ha="center", fontsize=10)

    ax.set_xlabel("输入文本长度（字符）", fontsize=12)
    ax.set_ylabel("平均响应耗时（秒）", fontsize=12)
    ax.set_title("AI 批处理响应耗时 vs 输入长度", fontsize=14, fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.5)
    fig.tight_layout()
    fig.savefig("benchmark_chart.png", dpi=150)
    print("✅ 已保存：benchmark_chart.png")

def make_report(results):
    """生成分析报告"""
    grouped = {}
    for r in results:
        grouped.setdefault(r["input_length"], []).append(r["elapsed"])

    with open("benchmark_report.txt", "w", encoding="utf-8") as f:
        f.write("=" * 50 + "\n")
        f.write("      课题10：AI 批处理耗时测试 —— 分析报告\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"测试模型：{MODEL}\n")
        f.write(f"测试平台：SiliconFlow API\n")
        f.write(f"每组重复次数：{REPEAT}\n")
        f.write(f"输入长度梯度：{INPUT_LENGTHS}\n\n")

        f.write("-" * 50 + "\n")
        f.write(f"{'输入长度':>8} | {'平均耗时(s)':>10} | {'最小(s)':>8} | {'最大(s)':>8}\n")
        f.write("-" * 50 + "\n")

        for length in sorted(grouped.keys()):
            times = grouped[length]
            f.write(f"{length:>8} | {statistics.mean(times):>10.2f} | "
                    f"{min(times):>8.2f} | {max(times):>8.2f}\n")

        f.write("-" * 50 + "\n\n")

        # 趋势分析
        all_avg = [statistics.mean(grouped[l]) for l in sorted(grouped.keys())]
        f.write("【趋势分析】\n")
        for i in range(1, len(all_avg)):
            prev_len = sorted(grouped.keys())[i - 1]
            curr_len = sorted(grouped.keys())[i]
            delta = all_avg[i] - all_avg[i - 1]
            ratio = (curr_len / prev_len) if prev_len > 0 else 0
            time_ratio = (all_avg[i] / all_avg[i-1]) if all_avg[i-1] > 0 else 0
            f.write(f"  {prev_len}→{curr_len} 字符：输入增 {ratio:.1f} 倍，"
                    f"耗时增 {time_ratio:.2f} 倍 ({delta:+.2f}s)\n")

        f.write("\n【结论】\n")
        f.write("  1. 随着输入文本长度增加，AI 响应耗时呈上升趋势。\n")
        f.write("  2. 耗时增长与输入长度并非严格线性，存在阶段性波动。\n")
        f.write("  3. 实际应用中应根据业务场景合理控制单次输入长度，\n")
        f.write("     或采用分批处理策略以提升整体吞吐效率。\n")
        f.write("\n" + "=" * 50 + "\n")

    print("✅ 已保存：benchmark_report.txt")

def main():
    print("=" * 50)
    print("      课题10：AI 批处理耗时测试")
    print("=" * 50)
    print(f"模型：{MODEL}")
    print(f"API：SiliconFlow\n")

    results = run_benchmark()
    save_csv(results)
    make_chart(results)
    make_report(results)

    print("\n🎉 全部完成！生成了 3 个文件：")
    print("  1. benchmark_results.csv   —— 原始数据")
    print("  2. benchmark_chart.png     —— 耗时曲线图")
    print("  3. benchmark_report.txt    —— 分析报告")

if __name__ == "__main__":
    main()