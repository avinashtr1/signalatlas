import os
import subprocess

WORKDIR = "/root/.openclaw/workspace"

def run(cmd, extra_env=None):
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)

    res = subprocess.run(
        cmd,
        cwd=WORKDIR,
        env=env,
        capture_output=True,
        text=True,
        shell=True,
        check=False,
    )

    return {
        "ok": res.returncode == 0,
        "stdout": (res.stdout or "").strip(),
        "stderr": (res.stderr or "").strip(),
        "returncode": res.returncode,
    }

def main():
    send_daily = os.getenv("ROUTE_DAILY_BRIEF", "1") == "1"
    send_tom = os.getenv("ROUTE_TOM_CARD", "1") == "1"
    send_alpha = os.getenv("ROUTE_ALPHA_FEED", "0") == "1"
    send_public = os.getenv("ROUTE_PUBLIC_TEASER", "0") == "1"

    print("SIGNALATLAS ALERT ROUTER")
    print("")
    print(f"daily_brief_enabled={send_daily}")
    print(f"tom_card_enabled={send_tom}")
    print(f"alpha_feed_enabled={send_alpha}")
    print(f"public_teaser_enabled={send_public}")
    print("")

    if send_daily:
        print("---- daily brief ----")
        r = run("SEND_TG=1 ./run_signalatlas_daily.sh")
        print(r["stdout"][-1500:])
        if r["stderr"]:
            print("stderr:", r["stderr"][-500:])
        print("")

    if send_tom:
        print("---- tom card (channel: tom_card) ----")
        r = run("./tom_send_card.sh", {"TOM_SEND_TG": "1"})
        print(r["stdout"][-800:])
        if r["stderr"]:
            print("stderr:", r["stderr"][-500:])
        print("")

    if send_alpha:
        print("---- alpha feed (channel: alpha_feed) ----")
        r = run("./tom_send_alpha_feed.sh", {"ALPHA_SEND_TG": "1"})
        print(r["stdout"][-800:])
        if r["stderr"]:
            print("stderr:", r["stderr"][-500:])
        print("")

    if send_public:
        print("---- public teaser (channel: public_teaser) ----")
        r = run("./tom_send_public_teaser.sh", {"PUBLIC_SEND_TG": "1"})
        print(r["stdout"][-800:])
        if r["stderr"]:
            print("stderr:", r["stderr"][-500:])
        print("")

if __name__ == "__main__":
    main()
