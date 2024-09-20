from prefect import flow

if __name__ == "__main__":
    flow.from_source(
        "https://github.com/alamyrjunior/freela-pulse_prefect",
        entrypoint="main.py:freela_pulse",
    ).deploy(
        name="freela-pulse",
        work_pool_name="docker-pool",
        build=False
    )