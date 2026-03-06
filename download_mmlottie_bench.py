#!/usr/bin/env python3
"""
MMLottieBench 数据集下载脚本

用途:
    从 HuggingFace 下载 OmniLottie/MMLottieBench 数据集并保存到本地

使用方法:
    python download_mmlottie_bench.py
    python download_mmlottie_bench.py --output_dir /custom/path

数据集结构:
    该数据集使用 HuggingFace Datasets 格式
    - Splits: real, synthetic
    - Task types: Text-to-Lottie, Text-Image-to-Lottie, Video-to-Lottie
    - Fields: id, text, image, video, task_type, subset, etc.

注意:
    数据集使用 Apache Arrow 格式存储，图像和视频已嵌入其中
    不需要手动解压！直接通过 datasets API 访问即可
"""

import os
import argparse
import sys
from pathlib import Path

try:
    from datasets import load_dataset
except ImportError:
    print("❌ Error: datasets library not installed")
    print("Please install it with: pip install datasets")
    sys.exit(1)


def download_and_save_dataset(output_dir):
    """
    从 HuggingFace 下载 MMLottieBench 数据集并保存到本地

    Args:
        output_dir: 保存路径

    Returns:
        bool: 下载是否成功
    """
    # 转换为绝对路径
    output_dir = os.path.abspath(output_dir)

    print("=" * 70)
    print("🎨 MMLottieBench Dataset Downloader")
    print("=" * 70)
    print(f"📦 Repository: OmniLottie/MMLottieBench")
    print(f"📁 Output directory: {output_dir}")
    print("=" * 70)
    print()

    # 检查目录是否已存在
    if os.path.exists(output_dir) and os.listdir(output_dir):
        print(f"⚠️  Directory already exists and is not empty: {output_dir}")
        response = input("Continue and overwrite? [y/N]: ")
        if response.lower() != 'y':
            print("❌ Download cancelled by user")
            return False
        print()

    try:
        print("📥 Step 1/2: Downloading dataset from HuggingFace...")
        print("⏳ This may take a while depending on your network speed...")
        print()

        # 下载数据集（会自动使用 HF 缓存）
        dataset = load_dataset("OmniLottie/MMLottieBench")

        print()
        print("📊 Dataset loaded successfully!")
        print(f"  Available splits: {list(dataset.keys())}")

        for split_name, split_data in dataset.items():
            print(f"  - {split_name}: {len(split_data)} samples")

            # 统计任务类型
            task_types = {}
            for sample in split_data:
                task_type = sample.get('task_type', 'Unknown')
                task_types[task_type] = task_types.get(task_type, 0) + 1

            for task_type, count in task_types.items():
                print(f"      • {task_type}: {count} samples")

        print()
        print("💾 Step 2/2: Saving dataset to disk...")

        # 保存到磁盘
        dataset.save_to_disk(output_dir)

        print()
        print("=" * 70)
        print("✅ Download and save completed successfully!")
        print("=" * 70)
        print(f"📁 Dataset saved to: {output_dir}")
        print()
        print("📖 Usage in Python:")
        print("  from datasets import load_from_disk")
        print(f"  dataset = load_from_disk('{output_dir}')")
        print("  real_data = dataset['real']")
        print("  synthetic_data = dataset['synthetic']")
        print()
        print("📖 Usage in inference:")
        print(f"  python inference.py --split real --sketch_weight <model>")
        print()
        print("💡 Note: Data is stored in Apache Arrow format")
        print("   Images and videos are embedded - no need to extract!")
        print("   Access them directly through the datasets API.")
        print()

        return True

    except KeyboardInterrupt:
        print("\n\n⚠️  Download interrupted by user")
        return False

    except Exception as e:
        print()
        print("=" * 70)
        print("❌ Download failed!")
        print("=" * 70)
        print(f"Error: {str(e)}")
        print()
        print("💡 Troubleshooting:")
        print("  1. Check your network connection")
        print("  2. Make sure you have write permission to the target directory")
        print("  3. Install required packages: pip install datasets")
        print("  4. Try setting HF mirror: export HF_ENDPOINT=https://hf-mirror.com")
        print()
        print("📖 Manual access:")
        print("  Visit: https://huggingface.co/datasets/OmniLottie/MMLottieBench")
        print("  Or use in Python:")
        print("    from datasets import load_dataset")
        print("    dataset = load_dataset('OmniLottie/MMLottieBench')")
        print("=" * 70)
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Download MMLottieBench dataset from HuggingFace',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download to default location
  python download_mmlottie_bench.py

  # Download to specific directory
  python download_mmlottie_bench.py --output_dir /data/datasets/mmlottie_bench

Dataset structure (Arrow format):
  mmlottie_bench/
  ├── dataset_dict.json
  ├── real/
  │   ├── data-00000-of-00001.arrow  (contains images, videos, text)
  │   ├── dataset_info.json
  │   └── state.json
  └── synthetic/
      └── (same structure)

About the dataset:
  MMLottieBench is a benchmark dataset for Lottie animation generation

  Splits:
    - real: Real-world Lottie animations (450 samples)
    - synthetic: Synthetically generated samples (450 samples)

  Task types (150 samples each per split):
    - Text-to-Lottie: Generate from text prompt
    - Text-Image-to-Lottie: Generate from text + image
    - Video-to-Lottie: Generate from video

  Data format:
    - Stored in Apache Arrow format (efficient, compressed)
    - Images: embedded as PIL.Image objects
    - Videos: embedded as VideoReader objects
    - Text: direct string storage
    - NO manual extraction needed!

Usage after download:
  1. In Python code:
     from datasets import load_from_disk
     dataset = load_from_disk('/data/cref/Lottie-kaiyuan/mmlottie_bench')
     real_data = dataset['real']

  2. In inference:
     python inference.py --split real --sketch_weight <model>

For more info, see:
  - MMLOTTIE_BENCH_USAGE.md
  - MMLOTTIE_BENCH_DATA_ACCESS.md
        """
    )

    parser.add_argument(
        '--output_dir',
        type=str,
        default='/data/cref/Lottie-kaiyuan/mmlottie_bench',
        help='Output directory to save the dataset (default: /data/cref/Lottie-kaiyuan/mmlottie_bench)'
    )

    args = parser.parse_args()

    # 执行下载
    success = download_and_save_dataset(args.output_dir)

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
