"""Train a small output-length baseline from labeled prompts.

This module is inspired by the public Prompt2Length abstract. It is a transparent
ridge-regression baseline, not a DistilBERT implementation or a paper reproduction.
"""

import argparse
import json
import math
import random
import re
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path

from .scheduling import LengthEstimate


SHORT_CUES = ("brief", "briefly", "concise", "concisely", "short", "一句话", "简要", "简短", "概述")
LONG_CUES = ("detailed", "detail", "thorough", "comprehensive", "in depth", "详细", "深入", "全面", "完整")
LIST_CUES = ("list", "steps", "points", "items", "sections", "列出", "步骤", "要点", "部分")
FEATURE_NAMES = ("word_units", "characters", "short_cues", "long_cues", "list_cues", "question_marks")


@dataclass(frozen=True)
class LengthObservation:
    prompt: str
    output_units: float


def prompt_features(prompt: str) -> list[float]:
    lower = prompt.lower()
    word_units = len(re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]", prompt))
    return [
        float(word_units),
        float(len(prompt)),
        float(sum(lower.count(cue) for cue in SHORT_CUES)),
        float(sum(lower.count(cue) for cue in LONG_CUES)),
        float(sum(lower.count(cue) for cue in LIST_CUES)),
        float(prompt.count("?") + prompt.count("？")),
    ]


def filter_normal_outliers(observations: list[LengthObservation], z_limit: float = 2.5) -> list[LengthObservation]:
    """Remove global output-length outliers using a configurable z-score rule."""
    if z_limit <= 0:
        raise ValueError("z_limit must be positive")
    if len(observations) < 3:
        return list(observations)
    values = [item.output_units for item in observations]
    deviation = statistics.pstdev(values)
    if deviation == 0:
        return list(observations)
    mean = statistics.fmean(values)
    return [item for item in observations if abs(item.output_units - mean) / deviation <= z_limit]


def augment_length_cues(observations: list[LengthObservation]) -> list[LengthObservation]:
    """Add deterministic cue substitutions while keeping the observed length label."""
    groups = (("briefly", "concisely"), ("detailed", "thorough"), ("简要", "简短"), ("详细", "全面"))
    result = list(observations)
    seen = {(item.prompt, item.output_units) for item in result}
    for item in observations:
        lower = item.prompt.lower()
        for first, second in groups:
            replacement = None
            if first in lower:
                replacement = re.sub(re.escape(first), second, item.prompt, flags=re.IGNORECASE)
            elif second in lower:
                replacement = re.sub(re.escape(second), first, item.prompt, flags=re.IGNORECASE)
            if replacement and (replacement, item.output_units) not in seen:
                result.append(LengthObservation(replacement, item.output_units))
                seen.add((replacement, item.output_units))
    return result


def _solve(matrix: list[list[float]], vector: list[float]) -> list[float]:
    size = len(vector)
    augmented = [matrix[row][:] + [vector[row]] for row in range(size)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-12:
            raise ValueError("training matrix is singular")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            augmented[row] = [a - factor * b for a, b in zip(augmented[row], augmented[column])]
    return [augmented[row][-1] for row in range(size)]


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - position) + ordered[upper] * (position - lower)


@dataclass
class LengthModel:
    means: list[float]
    scales: list[float]
    coefficients: list[float]
    short_boundary: float
    long_boundary: float
    training_records: int
    filtered_records: int
    augmented_records: int
    method: str = "standardized-ridge-baseline"

    @classmethod
    def fit(
        cls,
        observations: list[LengthObservation],
        z_limit: float = 2.5,
        augment: bool = True,
        ridge: float = 1.0,
    ) -> "LengthModel":
        if ridge <= 0:
            raise ValueError("ridge must be positive")
        if any(not item.prompt.strip() or not math.isfinite(item.output_units) or item.output_units <= 0 for item in observations):
            raise ValueError("observations need nonempty prompts and positive finite output_units")
        filtered = filter_normal_outliers(observations, z_limit)
        if len(filtered) < 3:
            raise ValueError("at least three observations must remain after filtering")
        expanded = augment_length_cues(filtered) if augment else filtered
        raw = [prompt_features(item.prompt) for item in expanded]
        means = [statistics.fmean(row[column] for row in raw) for column in range(len(FEATURE_NAMES))]
        scales = [statistics.pstdev(row[column] for row in raw) or 1.0 for column in range(len(FEATURE_NAMES))]
        rows = [[1.0] + [(value - means[i]) / scales[i] for i, value in enumerate(row)] for row in raw]
        outputs = [item.output_units for item in expanded]
        width = len(rows[0])
        normal = [[sum(row[i] * row[j] for row in rows) for j in range(width)] for i in range(width)]
        for index in range(1, width):
            normal[index][index] += ridge
        target = [sum(row[i] * output for row, output in zip(rows, outputs)) for i in range(width)]
        coefficients = _solve(normal, target)
        original_outputs = [item.output_units for item in filtered]
        return cls(
            means,
            scales,
            coefficients,
            _percentile(original_outputs, 1 / 3),
            _percentile(original_outputs, 2 / 3),
            len(observations),
            len(filtered),
            len(expanded),
        )

    def predict(self, prompt: str) -> float:
        features = prompt_features(prompt)
        standardized = [(value - self.means[i]) / self.scales[i] for i, value in enumerate(features)]
        prediction = self.coefficients[0] + sum(a * b for a, b in zip(self.coefficients[1:], standardized))
        return max(1.0, prediction)

    def estimate(self, prompt: str) -> LengthEstimate:
        prediction = self.predict(prompt)
        bucket = "short" if prediction <= self.short_boundary else "medium" if prediction <= self.long_boundary else "long"
        return LengthEstimate(bucket, round(prediction))

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "LengthModel":
        return cls(**json.loads(path.read_text(encoding="utf-8")))


def load_observations(path: Path) -> list[LengthObservation]:
    result = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            result.append(LengthObservation(**json.loads(line)))
        except (TypeError, json.JSONDecodeError) as error:
            raise ValueError(f"invalid observation on line {line_number}: {error}") from error
    return result


def evaluate(model: LengthModel, observations: list[LengthObservation]) -> dict[str, float]:
    if not observations:
        raise ValueError("evaluation data cannot be empty")
    errors = [abs(model.predict(item.prompt) - item.output_units) for item in observations]
    correct = 0
    for item in observations:
        actual = "short" if item.output_units <= model.short_boundary else "medium" if item.output_units <= model.long_boundary else "long"
        correct += model.estimate(item.prompt).bucket == actual
    return {"mae": statistics.fmean(errors), "bucket_accuracy": correct / len(observations)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Train an educational output-length ridge baseline.")
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--test-fraction", type=float, default=0.25)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--z-limit", type=float, default=2.5)
    parser.add_argument("--no-augment", action="store_true")
    args = parser.parse_args()
    if not 0 < args.test_fraction < 1:
        parser.error("--test-fraction must be between 0 and 1")
    try:
        records = load_observations(args.data)
        if len(records) < 8:
            raise ValueError("at least eight observations are required for a train/test demonstration")
        shuffled = records[:]
        random.Random(args.seed).shuffle(shuffled)
        split = min(len(shuffled) - 1, max(3, round(len(shuffled) * (1 - args.test_fraction))))
        train, test = shuffled[:split], shuffled[split:]
        evaluation_model = LengthModel.fit(train, args.z_limit, not args.no_augment)
        metrics = evaluate(evaluation_model, test)
        final_model = LengthModel.fit(records, args.z_limit, not args.no_augment)
        final_model.save(args.output)
    except ValueError as error:
        parser.error(str(error))
    print(f"Train/test records: {len(train)}/{len(test)}")
    print(f"Holdout MAE: {metrics['mae']:.3f} output units")
    print(f"Holdout bucket accuracy: {metrics['bucket_accuracy']:.3f}")
    print(f"Final records: {final_model.training_records} input, {final_model.filtered_records} filtered, {final_model.augmented_records} after augmentation")
    print(f"Saved model to {args.output}")


if __name__ == "__main__":
    main()
