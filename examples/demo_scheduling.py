"""Minimal FCFS versus predicted-shortest-first scheduling demonstration."""

import argparse

from research_agents.scheduling import simulate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lang", choices=("en", "zh"), default="en")
    args = parser.parse_args()
    actual_durations = [8, 2, 1]
    predicted_durations = [8, 2, 1]

    if args.lang == "zh":
        print("一个执行名额，三个任务均在时间 0 到达")
        print(f"实际时长：{actual_durations}\n")
    else:
        print("One worker, three tasks, all available at time 0")
        print(f"Actual durations: {actual_durations}\n")
    for policy in ("fcfs", "sjf"):
        result = simulate(actual_durations, predicted_durations, workers=1, policy=policy)
        order = [event.task_id + 1 for event in result["events"]]
        print(f"{policy.upper()} {'顺序' if args.lang == 'zh' else 'order'}: {order}")
        for event in result["events"]:
            if args.lang == "zh":
                print(f"  任务 {event.task_id + 1}：开始={event.start:g}，结束={event.finish:g}")
            else:
                print(f"  task {event.task_id + 1}: start={event.start:g}, finish={event.finish:g}")
        if args.lang == "zh":
            print(f"  平均等待时间：{result['mean_wait']:.3f}")
            print(f"  全部任务完成时间：{result['makespan']:.3f}\n")
        else:
            print(f"  mean wait: {result['mean_wait']:.3f}")
            print(f"  makespan: {result['makespan']:.3f}\n")


if __name__ == "__main__":
    main()
