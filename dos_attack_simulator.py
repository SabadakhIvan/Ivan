from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple
import json
import math
import random

import matplotlib.pyplot as plt


@dataclass
class SimulationConfig:
    duration_steps: int = 240
    normal_arrival_rate: float = 3.0
    attack_arrival_rate: float = 12.0
    attack_start_step: int = 80
    attack_end_step: int = 180
    service_capacity_per_step: int = 4
    queue_limit: int = 50
    seed: int = 42

    @classmethod
    def from_json(cls, path: str | Path) -> "SimulationConfig":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(**data)


def sample_poisson(lmbda: float, rng: random.Random) -> int:
    if lmbda <= 0:
        return 0
    # Knuth algorithm, sufficient for coursework-scale parameters.
    limit = math.exp(-lmbda)
    k = 0
    p = 1.0
    while p > limit:
        k += 1
        p *= rng.random()
    return k - 1


def _regime(step: int, cfg: SimulationConfig) -> str:
    return "attack" if cfg.attack_start_step <= step < cfg.attack_end_step else "normal"


def simulate(cfg: SimulationConfig) -> Dict[str, object]:
    rng = random.Random(cfg.seed)

    queue = 0
    queue_series: List[int] = []
    arrivals_series: List[int] = []
    served_series: List[int] = []
    dropped_series: List[int] = []
    waiting_time_proxy: List[float] = []
    regime_series: List[str] = []

    total_arrivals = 0
    total_served = 0
    total_dropped = 0
    peak_queue = 0

    normal_steps = 0
    attack_steps = 0
    normal_served = 0
    attack_served = 0
    normal_dropped = 0
    attack_dropped = 0

    for step in range(cfg.duration_steps):
        regime = _regime(step, cfg)
        regime_series.append(regime)
        if regime == "attack":
            lmbda = cfg.attack_arrival_rate
            attack_steps += 1
        else:
            lmbda = cfg.normal_arrival_rate
            normal_steps += 1

        arrivals = sample_poisson(lmbda, rng)
        total_arrivals += arrivals

        accepted = min(arrivals, max(0, cfg.queue_limit - queue))
        dropped = arrivals - accepted
        queue += accepted

        served = min(queue, cfg.service_capacity_per_step)
        queue -= served

        total_served += served
        total_dropped += dropped
        peak_queue = max(peak_queue, queue)

        if regime == "attack":
            attack_served += served
            attack_dropped += dropped
        else:
            normal_served += served
            normal_dropped += dropped

        queue_series.append(queue)
        arrivals_series.append(arrivals)
        served_series.append(served)
        dropped_series.append(dropped)
        waiting_time_proxy.append(queue / max(1, cfg.service_capacity_per_step))

    stats = {
        "total_arrivals": total_arrivals,
        "total_served": total_served,
        "total_dropped": total_dropped,
        "drop_rate": (total_dropped / total_arrivals) if total_arrivals else 0.0,
        "service_rate": (total_served / total_arrivals) if total_arrivals else 0.0,
        "peak_queue": peak_queue,
        "average_queue": sum(queue_series) / len(queue_series) if queue_series else 0.0,
        "average_wait_proxy": sum(waiting_time_proxy) / len(waiting_time_proxy) if waiting_time_proxy else 0.0,
        "normal_average_served": normal_served / max(1, normal_steps),
        "attack_average_served": attack_served / max(1, attack_steps),
        "normal_average_dropped": normal_dropped / max(1, normal_steps),
        "attack_average_dropped": attack_dropped / max(1, attack_steps),
    }

    return {
        "config": cfg,
        "stats": stats,
        "series": {
            "queue": queue_series,
            "arrivals": arrivals_series,
            "served": served_series,
            "dropped": dropped_series,
            "wait_proxy": waiting_time_proxy,
            "regime": regime_series,
        },
    }


def render_charts(result: Dict[str, object], output_dir: str | Path) -> List[Path]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    cfg: SimulationConfig = result["config"]  # type: ignore[assignment]
    series: Dict[str, List[float]] = result["series"]  # type: ignore[assignment]
    steps = list(range(cfg.duration_steps))

    created: List[Path] = []

    plt.figure(figsize=(10, 5))
    plt.plot(steps, series["arrivals"], label="Надходження запитів")
    plt.plot(steps, series["served"], label="Оброблено запитів")
    plt.axvspan(cfg.attack_start_step, cfg.attack_end_step, alpha=0.2, label="Період атаки")
    plt.xlabel("Крок моделювання")
    plt.ylabel("Кількість запитів")
    plt.title("Динаміка надходження та обробки запитів")
    plt.legend()
    plt.tight_layout()
    path1 = output_path / "request_dynamics.png"
    plt.savefig(path1, dpi=160)
    plt.close()
    created.append(path1)

    plt.figure(figsize=(10, 5))
    plt.plot(steps, series["queue"], label="Довжина черги")
    plt.plot(steps, series["wait_proxy"], label="Умовний час очікування")
    plt.axvspan(cfg.attack_start_step, cfg.attack_end_step, alpha=0.2, label="Період атаки")
    plt.xlabel("Крок моделювання")
    plt.ylabel("Значення")
    plt.title("Черга та умовний час очікування")
    plt.legend()
    plt.tight_layout()
    path2 = output_path / "queue_waiting.png"
    plt.savefig(path2, dpi=160)
    plt.close()
    created.append(path2)

    plt.figure(figsize=(10, 5))
    plt.bar(steps, series["dropped"], width=1.0)
    plt.axvspan(cfg.attack_start_step, cfg.attack_end_step, alpha=0.2, label="Період атаки")
    plt.xlabel("Крок моделювання")
    plt.ylabel("Втрачені запити")
    plt.title("Кількість відхилених запитів під час моделювання")
    plt.legend()
    plt.tight_layout()
    path3 = output_path / "dropped_requests.png"
    plt.savefig(path3, dpi=160)
    plt.close()
    created.append(path3)

    return created


def build_report(result: Dict[str, object]) -> str:
    cfg: SimulationConfig = result["config"]  # type: ignore[assignment]
    stats: Dict[str, float] = result["stats"]  # type: ignore[assignment]

    lines = [
        "ЗВІТ ПРО РЕЗУЛЬТАТИ МОДЕЛЮВАННЯ DoS-АТАКИ",
        "=" * 52,
        "",
        "1. ПАРАМЕТРИ МОДЕЛІ",
        f"Тривалість моделювання: {cfg.duration_steps} кроків",
        f"Інтенсивність надходження у штатному режимі: {cfg.normal_arrival_rate:.2f}",
        f"Інтенсивність надходження під час атаки: {cfg.attack_arrival_rate:.2f}",
        f"Початок атаки: крок {cfg.attack_start_step}",
        f"Кінець атаки: крок {cfg.attack_end_step}",
        f"Пропускна здатність вузла: {cfg.service_capacity_per_step} зап./крок",
        f"Максимальна довжина черги: {cfg.queue_limit}",
        "",
        "2. ЗАГАЛЬНІ РЕЗУЛЬТАТИ",
        f"Загальна кількість вхідних запитів: {int(stats['total_arrivals'])}",
        f"Оброблено запитів: {int(stats['total_served'])}",
        f"Втрачено запитів: {int(stats['total_dropped'])}",
        f"Частка відхилених запитів: {stats['drop_rate'] * 100:.2f}%",
        f"Частка успішно оброблених запитів: {stats['service_rate'] * 100:.2f}%",
        f"Максимальна довжина черги: {int(stats['peak_queue'])}",
        f"Середня довжина черги: {stats['average_queue']:.2f}",
        f"Умовний середній час очікування: {stats['average_wait_proxy']:.2f}",
        "",
        "3. ПОРІВНЯННЯ РЕЖИМІВ",
        f"Середня кількість оброблених запитів у штатному режимі: {stats['normal_average_served']:.2f}",
        f"Середня кількість оброблених запитів під час атаки: {stats['attack_average_served']:.2f}",
        f"Середня кількість втрачених запитів у штатному режимі: {stats['normal_average_dropped']:.2f}",
        f"Середня кількість втрачених запитів під час атаки: {stats['attack_average_dropped']:.2f}",
        "",
        "4. ВИСНОВОК",
    ]

    if stats["total_dropped"] > 0:
        lines.append(
            "У моделі DoS-атака призвела до перевищення допустимого навантаження на вузол, "
            "зростання черги та появи втрат запитів. Це підтверджує зниження доступності сервісу "
            "в умовах перевантаження."
        )
    else:
        lines.append(
            "У заданих параметрах вузол зберіг працездатність навіть у період атаки. "
            "Для демонстрації наслідків DoS-атаки доцільно збільшити інтенсивність вхідного потоку "
            "або зменшити пропускну здатність вузла."
        )
    return "\n".join(lines)


def save_report(report_text: str, output_dir: str | Path) -> Path:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    report_file = output_path / "dos_report.txt"
    report_file.write_text(report_text, encoding="utf-8")
    return report_file
