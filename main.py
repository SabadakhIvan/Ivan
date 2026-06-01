from __future__ import annotations

import argparse
from pathlib import Path

from dos_attack_simulator import (
    SimulationConfig,
    build_report,
    render_charts,
    save_report,
    simulate,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Моделювання DoS-атаки на вузол мережі та аналіз її наслідків"
    )
    parser.add_argument("--config", default="demo_config.json", help="Шлях до JSON-файлу з параметрами моделі")
    parser.add_argument("--output-dir", default="outputs", help="Папка для збереження звіту та графіків")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg_path = Path(args.config)
    if not cfg_path.exists():
        raise FileNotFoundError(f"Не знайдено файл конфігурації: {cfg_path}")

    config = SimulationConfig.from_json(cfg_path)
    result = simulate(config)
    charts = render_charts(result, args.output_dir)
    report_text = build_report(result)
    report_path = save_report(report_text, args.output_dir)

    print(report_text)
    print("\nСтворено файли:")
    for chart in charts:
        print(f"- {chart}")
    print(f"- {report_path}")


if __name__ == "__main__":
    main()
