"""Constrained, evidence-grounded investigation assistant.

Typed commands are interpreted deterministically. Speech transcription is an
optional provider adapter and never receives investigation data.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .config import settings
from .models import (
    Account,
    AccountScore,
    AnalysisRun,
    BlockchainDataset,
    BlockchainDecision,
    BlockchainReferenceLabel,
    BlockchainRelationship,
    BlockchainWallet,
    BlockchainWalletScore,
    Dataset,
    Decision,
    Finding,
    Transaction,
)


ALLOWED_COMMANDS = {
    "filter_high_risk",
    "open_wallet",
    "explain_wallet",
    "expand_network",
    "supporting_transactions",
    "summarize_investigation",
    "missing_data",
    "propose_decision",
}


@dataclass(frozen=True)
class ParsedCommand:
    tool: str
    arguments: dict[str, Any]


def parse_command(text: str) -> ParsedCommand:
    normalized = " ".join(text.strip().split())
    lower = normalized.lower().rstrip(".?!")
    if not normalized or len(normalized) > 800:
        raise ValueError("Command must contain between 1 and 800 characters")
    if re.search(r"\b(show|list|filter)\b.*\bhigh[- ]risk\b", lower):
        return ParsedCommand("filter_high_risk", {})
    match = re.match(r"^(?:open|select|find|show)\s+(?:wallet|account)\s+(.+)$", normalized, re.I)
    if match:
        identifier = match.group(1).strip().strip('"\'')
        return ParsedCommand("open_wallet", {"query": identifier[:180]})
    if re.search(r"\bwhy\b.*\b(?:wallet|account|flagged)\b|\bexplain\b.*\b(?:wallet|account|finding)", lower):
        return ParsedCommand("explain_wallet", {})
    if re.search(r"\bexpand\b.*\b(?:network|neighborhood|graph)\b", lower):
        return ParsedCommand("expand_network", {})
    if re.search(r"\b(?:supporting|related)\b.*\b(?:transactions|transfers|evidence)\b", lower):
        return ParsedCommand("supporting_transactions", {})
    if re.search(r"\bsummari[sz]e\b.*\b(?:investigation|wallet|account|evidence|case)\b", lower):
        return ParsedCommand("summarize_investigation", {})
    if re.search(r"\b(?:what|which)\b.*\b(?:data|fields?)\b.*\b(?:missing|unavailable)|\bwhat data is missing\b", lower):
        return ParsedCommand("missing_data", {})
    if re.search(r"\b(?:confirm|mark)\b.*\b(?:suspicious|fraud)\b", lower):
        return ParsedCommand("propose_decision", {"status": "confirmed_suspicious"})
    if re.search(r"\b(?:clear|mark)\b.*\b(?:wallet|account|legitimate|safe)\b", lower):
        return ParsedCommand("propose_decision", {"status": "cleared"})
    raise ValueError("Unsupported command. Try filtering risk, opening a wallet, explaining findings, expanding the network, showing evidence, or summarizing the investigation.")


def _dataset(db: Session, dataset_id: int, workspace_id: int) -> Dataset:
    row = db.scalar(select(Dataset).where(Dataset.id == dataset_id, Dataset.workspace_id == workspace_id))
    if not row:
        raise HTTPException(404, "Dataset not found")
    return row


def _run(db: Session, run_id: int, workspace_id: int) -> AnalysisRun:
    row = db.scalar(select(AnalysisRun).join(Dataset).where(AnalysisRun.id == run_id, Dataset.workspace_id == workspace_id))
    if not row:
        raise HTTPException(404, "Analysis run not found")
    return row


def _blockchain_dataset(db: Session, dataset_id: int, workspace_id: int) -> BlockchainDataset:
    row = db.scalar(select(BlockchainDataset).where(BlockchainDataset.id == dataset_id, BlockchainDataset.workspace_id == workspace_id))
    if not row:
        raise HTTPException(404, "Blockchain dataset not found")
    return row


def _ref(kind: str, identifier: str | int, label: str, **extra: Any) -> dict[str, Any]:
    return {"kind": kind, "id": str(identifier), "label": label, **extra}


def _need_wallet(request_id: str) -> dict[str, Any]:
    return {
        "request_id": request_id,
        "status": "clarification",
        "answer": "Select a wallet or account first, then try that command again.",
        "spoken_answer": "Please select a wallet first.",
        "action": {"type": "none"},
        "evidence": [],
        "choices": [],
    }


def execute_command(db: Session, user: Any, request_id: str, text: str, context: dict[str, Any]) -> dict[str, Any]:
    parsed = parse_command(text)
    if parsed.tool not in ALLOWED_COMMANDS:
        raise HTTPException(422, "Unsupported assistant tool")
    domain = context.get("domain")
    if domain not in {"bank", "elliptic"}:
        raise HTTPException(422, "Investigation domain must be bank or elliptic")
    dataset_id = context.get("dataset_id")
    run_id = context.get("run_id")
    selected = (context.get("wallet_id") or "").strip()
    if not isinstance(dataset_id, int):
        raise HTTPException(422, "A selected dataset is required")
    dataset: Dataset | BlockchainDataset
    if domain == "bank":
        dataset = _dataset(db, dataset_id, user.workspace_id)
        if parsed.tool != "missing_data":
            if not isinstance(run_id, int):
                raise HTTPException(422, "A completed analysis run is required")
            run = _run(db, run_id, user.workspace_id)
            if run.dataset_id != dataset.id:
                raise HTTPException(422, "Analysis run does not belong to the selected dataset")
    else:
        dataset = _blockchain_dataset(db, dataset_id, user.workspace_id)

    base = {
        "request_id": request_id,
        "status": "completed",
        "dataset_id": dataset.id,
        "run_id": run_id if domain == "bank" else None,
        "domain": domain,
        "choices": [],
    }

    if parsed.tool == "filter_high_risk":
        if domain == "bank":
            count = db.scalar(select(func.count()).select_from(AccountScore).where(AccountScore.run_id == run_id, AccountScore.severity == "High")) or 0
        else:
            count = db.scalar(select(func.count()).select_from(BlockchainWalletScore).where(BlockchainWalletScore.dataset_id == dataset.id, BlockchainWalletScore.severity == "High")) or 0
        return {**base, "answer": f"Applied the High-risk filter. {count} flagged {('accounts' if domain == 'bank' else 'wallets')} match in this investigation scope.", "spoken_answer": f"Showing {count} high-risk {'accounts' if domain == 'bank' else 'wallets'}.", "action": {"type": "filter_high_risk", "severity": "High"}, "evidence": [_ref("dataset", dataset.id, dataset.name)]}

    if parsed.tool == "open_wallet":
        query = parsed.arguments["query"]
        if domain == "bank":
            stmt = select(AccountScore).where(AccountScore.run_id == run_id, AccountScore.account_id.contains(query)).order_by(AccountScore.score.desc()).limit(8)
            rows = db.scalars(stmt).all()
            values = [{"id": x.account_id, "label": x.account_id, "score": x.score, "severity": x.severity} for x in rows]
        else:
            stmt = select(BlockchainWalletScore).where(BlockchainWalletScore.dataset_id == dataset.id, BlockchainWalletScore.address.contains(query)).order_by(BlockchainWalletScore.score.desc()).limit(8)
            rows = db.scalars(stmt).all()
            values = [{"id": x.address, "label": x.address, "score": x.score, "severity": x.severity} for x in rows]
        exact = next((x for x in values if x["id"].lower() == query.lower()), None)
        if exact or len(values) == 1:
            chosen = exact or values[0]
            return {**base, "answer": f"Resolved and selected {chosen['id']} before opening its evidence.", "spoken_answer": "The requested wallet is selected.", "action": {"type": "select_wallet", "wallet_id": chosen["id"]}, "evidence": [_ref("wallet" if domain == "elliptic" else "account", chosen["id"], chosen["id"]) ]}
        if not values:
            return {**base, "status": "clarification", "answer": f"No {('account' if domain == 'bank' else 'wallet')} matched “{query}”. Edit the identifier and try again.", "spoken_answer": "I could not find that identifier.", "action": {"type": "none"}, "evidence": []}
        return {**base, "status": "clarification", "answer": f"“{query}” matches several identifiers. Choose the exact one below before I update the investigation.", "spoken_answer": "Several identifiers match. Please choose one on screen.", "action": {"type": "choose_wallet"}, "evidence": [], "choices": values}

    if parsed.tool in {"explain_wallet", "supporting_transactions", "summarize_investigation", "expand_network", "propose_decision"} and not selected:
        return {**base, **_need_wallet(request_id)}

    if parsed.tool == "expand_network":
        return {**base, "answer": f"Expanding the bounded neighborhood around {selected}. The graph will update only after the authorized network request succeeds.", "spoken_answer": "Expanding the selected network.", "action": {"type": "expand_network", "wallet_id": selected}, "evidence": [_ref("wallet" if domain == "elliptic" else "account", selected, selected)]}

    if parsed.tool == "propose_decision":
        status = parsed.arguments["status"]
        return {**base, "answer": f"Prepared a proposed decision for {selected}: {status.replace('_', ' ')}. Enter an analyst note and confirm it on screen; a spoken yes cannot submit it.", "spoken_answer": "The decision form is ready for your written note and on-screen confirmation.", "action": {"type": "open_decision_form", "wallet_id": selected, "status": status}, "evidence": [_ref("wallet" if domain == "elliptic" else "account", selected, selected)]}

    if parsed.tool == "missing_data":
        if domain == "elliptic":
            capabilities = dataset.capabilities or {}
            missing = [f"{name.replace('_', ' ')}: {item.get('reason') or 'unavailable'}" for name, item in capabilities.items() if not item.get("available")]
            answer = "Unavailable capabilities for this Elliptic++ subset: " + ("; ".join(missing[:8]) if missing else "none reported.") + " Ordinal time steps are not exact timestamps, normalized features are not currency amounts, and a wallet address is not assumed to identify a person."
        else:
            accounts = db.scalars(select(Account).where(Account.dataset_id == dataset.id)).all()
            shared = any(x.created_at and (x.device_id or x.ip_address or x.kyc_group_id) for x in accounts)
            answer = "Exact transaction timestamps and documented transfer amounts are available for this bank dataset. " + ("Device, IP, or KYC linkage is available for some accounts." if shared else "Shared device, IP, and KYC analysis is disabled because those attributes and compatible creation dates are missing.")
        return {**base, "answer": answer, "spoken_answer": answer[:260], "action": {"type": "none"}, "evidence": [_ref("dataset", dataset.id, dataset.name)]}

    if domain == "bank":
        score = db.scalar(select(AccountScore).where(AccountScore.run_id == run_id, AccountScore.account_id == selected))
        if not score:
            raise HTTPException(404, "Flagged account not found")
        findings = db.scalars(select(Finding).where(Finding.run_id == run_id, Finding.id.in_(score.finding_ids))).all() if score.finding_ids else []
        transaction_ids = list(dict.fromkeys(t for finding in findings for t in finding.transaction_ids))[:20]
        transactions = db.scalars(select(Transaction).where(Transaction.dataset_id == dataset.id, Transaction.transaction_id.in_(transaction_ids))).all() if transaction_ids else []
        decisions = db.scalars(select(Decision).where(Decision.score_id == score.id).order_by(Decision.created_at.desc()).limit(10)).all()
        refs = [_ref("finding", x.id, x.detector.replace("_", " ").title(), wallet_id=selected) for x in findings[:8]]
        refs += [_ref("transaction", x.transaction_id, x.transaction_id, wallet_id=selected) for x in transactions[:12]]
        if parsed.tool == "supporting_transactions":
            answer = f"Found {len(transactions)} supporting transactions attached to {len(findings)} automated findings for {selected}. The evidence panel is open; amounts retain their documented currencies."
            action = {"type": "show_evidence", "wallet_id": selected, "transaction_ids": [x.transaction_id for x in transactions]}
        elif parsed.tool == "explain_wallet":
            reasons = "; ".join(x.reason for x in findings[:3]) or "No finding explanation is available."
            answer = f"{selected} has an automated prioritization score of {score.score}/100 ({score.severity}), not a fraud probability. Evidence: {reasons}"
            action = {"type": "show_evidence", "wallet_id": selected}
        else:
            latest = decisions[0] if decisions else None
            answer = f"Investigation summary for {selected}: automated score {score.score}/100 ({score.severity}); {len(findings)} findings; {len(transactions)} supporting transactions; analyst status {score.review_status}. " + (f"Latest analyst note: {latest.note}" if latest and latest.note else "No analyst note has been recorded.") + " Automated findings and analyst decisions remain separate."
            action = {"type": "show_evidence", "wallet_id": selected}
    else:
        wallet = db.scalar(select(BlockchainWallet).where(BlockchainWallet.dataset_id == dataset.id, BlockchainWallet.address == selected))
        score = db.scalar(select(BlockchainWalletScore).where(BlockchainWalletScore.dataset_id == dataset.id, BlockchainWalletScore.address == selected))
        if not wallet or not score:
            raise HTTPException(404, "Wallet not found")
        label = db.scalar(select(BlockchainReferenceLabel).where(BlockchainReferenceLabel.dataset_id == dataset.id, BlockchainReferenceLabel.node_type == "wallet", BlockchainReferenceLabel.node_id == selected))
        decisions = db.scalars(select(BlockchainDecision).where(BlockchainDecision.score_id == score.id).order_by(BlockchainDecision.created_at.desc()).limit(10)).all()
        relations = db.scalars(select(BlockchainRelationship).where(BlockchainRelationship.dataset_id == dataset.id, or_(BlockchainRelationship.source_id == selected, BlockchainRelationship.target_id == selected)).limit(20)).all()
        refs = [_ref("relationship", x.id, f"{x.relationship_type}: {x.source_id} → {x.target_id}", wallet_id=selected) for x in relations]
        refs.insert(0, _ref("wallet", selected, selected))
        if parsed.tool == "supporting_transactions":
            answer = f"The evidence panel shows {len(relations)} official directed relationships near {selected}. Elliptic++ does not document edge-level amounts or exact timestamps here, so none are inferred."
            action = {"type": "show_evidence", "wallet_id": selected, "relationship_ids": [x.id for x in relations]}
        elif parsed.tool == "explain_wallet":
            reasons = "; ".join(score.reasons[:3]) or "No structural threshold crossed."
            answer = f"{selected} has an automated structural score of {score.score}/100 ({score.severity}), not a fraud probability. Structural evidence: {reasons} Dataset label: {label.label_name if label else 'unavailable'}; this reference label is not a MADs prediction and was not used as detector input."
            action = {"type": "show_evidence", "wallet_id": selected}
        else:
            latest = decisions[0] if decisions else None
            answer = f"Investigation summary for wallet {selected}: structural score {score.score}/100 ({score.severity}); {len(score.reasons)} structural reasons; {len(relations)} nearby official relationships; analyst status {score.review_status}. " + (f"Latest analyst note: {latest.note}. " if latest and latest.note else "No analyst note has been recorded. ") + "This bounded historical Bitcoin subset lacks exact timestamps, edge amounts, balances, devices, IPs, KYC, and verified identities."
            action = {"type": "show_evidence", "wallet_id": selected}
    return {**base, "answer": answer[:4000], "spoken_answer": answer[:320], "action": action, "evidence": refs[:20]}


class SpeechProvider:
    async def transcribe(self, audio: bytes, filename: str, content_type: str) -> str:
        raise NotImplementedError


class DisabledSpeechProvider(SpeechProvider):
    async def transcribe(self, audio: bytes, filename: str, content_type: str) -> str:
        raise HTTPException(503, "Speech transcription is not configured. Typed commands remain available.")


class OpenAISpeechProvider(SpeechProvider):
    async def transcribe(self, audio: bytes, filename: str, content_type: str) -> str:
        if not settings.speech_api_key:
            raise HTTPException(503, "Speech transcription credentials are not configured. Typed commands remain available.")
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=8.0)) as client:
                response = await client.post(
                    f"{settings.speech_api_base.rstrip('/')}/audio/transcriptions",
                    headers={"Authorization": f"Bearer {settings.speech_api_key}"},
                    data={"model": settings.speech_transcription_model},
                    files={"file": (filename, audio, content_type)},
                )
            response.raise_for_status()
            text = str(response.json().get("text") or "").strip()
            if not text:
                raise HTTPException(502, "The speech service returned an empty transcript")
            return text[:800]
        except HTTPException:
            raise
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(502, "Speech transcription failed; edit or type the command and try again") from exc


class ElevenLabsSpeechProvider(SpeechProvider):
    async def transcribe(self, audio: bytes, filename: str, content_type: str) -> str:
        if not settings.elevenlabs_api_key:
            raise HTTPException(503, "ElevenLabs credentials are not configured. Typed commands remain available.")
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(45.0, connect=8.0)) as client:
                response = await client.post(
                    f"{settings.elevenlabs_api_base.rstrip('/')}/speech-to-text",
                    headers={"xi-api-key": settings.elevenlabs_api_key},
                    data={"model_id": settings.elevenlabs_stt_model},
                    files={"file": (filename, audio, content_type)},
                )
            response.raise_for_status()
            text = str(response.json().get("text") or "").strip()
            if not text:
                raise HTTPException(502, "ElevenLabs returned an empty transcript")
            return text[:800]
        except HTTPException:
            raise
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(502, "ElevenLabs transcription failed; edit or type the command and try again") from exc

    async def synthesize(self, text: str) -> tuple[bytes, str]:
        if not settings.elevenlabs_api_key:
            raise HTTPException(503, "ElevenLabs voice output is not configured")
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(45.0, connect=8.0)) as client:
                response = await client.post(
                    f"{settings.elevenlabs_api_base.rstrip('/')}/text-to-speech/{settings.elevenlabs_voice_id}",
                    params={"output_format": "mp3_44100_128"},
                    headers={"xi-api-key": settings.elevenlabs_api_key, "Content-Type": "application/json"},
                    json={
                        "text": text[:800],
                        "model_id": settings.elevenlabs_tts_model,
                        "voice_settings": {
                            "stability": 0.42,
                            "similarity_boost": 0.78,
                            "style": 0.28,
                            "use_speaker_boost": True,
                            "speed": 0.96,
                        },
                    },
                )
            response.raise_for_status()
            if not response.content:
                raise HTTPException(502, "ElevenLabs returned empty audio")
            return response.content, "audio/mpeg"
        except HTTPException:
            raise
        except httpx.HTTPError as exc:
            raise HTTPException(502, "ElevenLabs voice generation failed") from exc


def speech_provider() -> SpeechProvider:
    if settings.speech_provider.lower() == "elevenlabs":
        return ElevenLabsSpeechProvider()
    if settings.speech_provider.lower() == "openai":
        return OpenAISpeechProvider()
    return DisabledSpeechProvider()


async def synthesize_speech(text: str) -> tuple[bytes, str]:
    if settings.speech_provider.lower() != "elevenlabs":
        raise HTTPException(503, "ElevenLabs voice output is not configured")
    return await ElevenLabsSpeechProvider().synthesize(text)
