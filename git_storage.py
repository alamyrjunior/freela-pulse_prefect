from prefect import flow

if __name__ == "__main__":
    flow.from_source(
        "https://github.com/my_github_account/my_repo/my_file.git",
        entrypoint="flows/no-image.py:hello_world",
    ).deploy(
        name="no-image-deployment",
        work_pool_name="my-docker-pool",
        build=False
    )