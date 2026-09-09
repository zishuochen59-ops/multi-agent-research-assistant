"""Minimal FCFS versus predicted-shortest-first scheduling demonstration."""

from research_agents.scheduling import simulate


def main() -> None:
    actual_durations = [8, 2, 1]
    predicted_durations = [8, 2, 1]

    print("One worker, three tasks, all available at time 0")
    print(f"Actual durations: {actual_durations}\n")
    for policy in ("fcfs", "sjf"):
        result = simulate(actual_durations, predicted_durations, workers=1, policy=policy)
        order = [event.task_id + 1 for event in result["events"]]
        print(f"{policy.upper()} order: {order}")
        for event in result["events"]:
            print(
                f"  task {event.task_id + 1}: "
                f"start={event.start:g}, finish={event.finish:g}"
            )
        print(f"  mean wait: {result['mean_wait']:.3f}")
        print(f"  makespan: {result['makespan']:.3f}\n")


if __name__ == "__main__":
    main()
