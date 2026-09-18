def dummy_optimizer(demand, solar, tariff, battery_capacity):
    """
    Temporary optimizer.
    Replace this function with your teammate's optimization module.
    """

    schedule = []

    for i in range(24):
        if solar[i] > demand[i]:
            schedule.append(
                round(min(solar[i]-demand[i], battery_capacity), 2)
            )
        else:
            schedule.append(0)

    total_cost = sum(
        max(demand[i]-solar[i], 0) * tariff[i]
        for i in range(24)
    )

    return schedule, round(total_cost, 2)


def process_energy_request(data):

    schedule, cost = dummy_optimizer(
        data.demand,
        data.solar,
        data.tariff,
        data.battery_capacity
    )

    return schedule, cost
