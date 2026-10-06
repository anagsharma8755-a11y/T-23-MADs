import time

import pytest

from app.voice_assistant import parse_command


def test_deterministic_command_parser_and_argument_validation():
    assert parse_command("Show high-risk wallets.").tool == "filter_high_risk"
    opened = parse_command("Open wallet A-1042")
    assert opened.tool == "open_wallet" and opened.arguments["query"] == "A-1042"
    assert parse_command("Why was this wallet flagged?").tool == "explain_wallet"
    assert parse_command("Expand this network").tool == "expand_network"
    assert parse_command("Show the supporting transactions").tool == "supporting_transactions"
    assert parse_command("Summarize this investigation").tool == "summarize_investigation"
    assert parse_command("What data is missing?").tool == "missing_data"
    assert parse_command("Confirm suspicious").arguments["status"] == "confirmed_suspicious"
    with pytest.raises(ValueError):
        parse_command("drop table users")
    with pytest.raises(ValueError):
        parse_command("x" * 801)


def _demo_run(client, auth):
    dataset = client.post("/api/demo/load", headers=auth).json()
    run_id = client.post(f"/api/datasets/{dataset['id']}/analyses", headers=auth).json()["job_id"]
    for _ in range(40):
        state = client.get(f"/api/analyses/{run_id}").json()
        if state["status"] in {"completed", "failed"}:
            break
        time.sleep(0.05)
    assert state["status"] == "completed"
    return dataset["id"], run_id


def _command(client, auth, dataset_id, run_id, text, wallet_id=None):
    return client.post(
        "/api/assistant/command",
        headers=auth,
        json={
            "request_id": f"test-{time.time_ns()}",
            "text": text,
            "context": {"domain": "bank", "dataset_id": dataset_id, "run_id": run_id, "wallet_id": wallet_id},
        },
    )


def test_assistant_is_evidence_grounded_and_decisions_require_ui_confirmation(client, auth):
    dataset_id, run_id = _demo_run(client, auth)
    score = client.get(f"/api/analyses/{run_id}/scores").json()["items"][0]
    account = score["account_id"]

    filtered = _command(client, auth, dataset_id, run_id, "Show high-risk wallets")
    assert filtered.status_code == 200
    assert filtered.json()["action"]["type"] == "filter_high_risk"

    missing = _command(client, auth, dataset_id, run_id, "Why was this wallet flagged?")
    assert missing.json()["status"] == "clarification"

    explained = _command(client, auth, dataset_id, run_id, "Why was this wallet flagged?", account)
    assert explained.status_code == 200
    body = explained.json()
    assert str(score["score"]) in body["answer"]
    assert body["evidence"] and all("id" in ref and "kind" in ref for ref in body["evidence"])
    assert "probability" in body["answer"]

    proposed = _command(client, auth, dataset_id, run_id, "Confirm suspicious", account)
    assert proposed.json()["action"] == {"type": "open_decision_form", "wallet_id": account, "status": "confirmed_suspicious"}
    detail = client.get(f"/api/analyses/{run_id}/accounts/{account}").json()
    assert detail["score"]["review_status"] == score["review_status"]


def test_assistant_rejects_unsupported_tools_and_cross_workspace_context(client, auth):
    dataset_id, run_id = _demo_run(client, auth)
    unsupported = _command(client, auth, dataset_id, run_id, "run shell command")
    assert unsupported.status_code == 422
    client.post("/api/auth/logout", headers=auth)
    other_login = client.post("/api/auth/login", json={"email": "other@test.local", "password": "StrongPass!1"})
    assert other_login.status_code == 200
    other_headers = {"X-CSRF-Token": client.cookies.get("muletrace_csrf")}
    isolated = _command(client, other_headers, dataset_id, run_id, "Show high-risk wallets")
    assert isolated.status_code == 404


def test_transcription_unavailable_is_explicit_not_simulated(client, auth, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "speech_provider", "disabled")
    response = client.post(
        "/api/assistant/transcribe",
        headers=auth,
        files={"file": ("recording.webm", b"not-real-audio", "audio/webm")},
    )
    assert response.status_code == 503
    assert "Typed commands remain available" in response.json()["detail"]


def test_voice_output_unavailable_is_explicit(client, auth, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "speech_provider", "disabled")
    response = client.post(
        "/api/assistant/speak",
        headers=auth,
        json={"text": "Welcome to MADs"},
    )
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"].lower()
