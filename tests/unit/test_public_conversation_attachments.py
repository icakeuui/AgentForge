import json
import time
import uuid

import pytest

from backend.core.exceptions import ValidationException
from backend.services.public_conversation_attachment_service import (
    LocalAttachmentStorage,
    PublicConversationAttachmentService,
)


def test_public_attachment_is_scoped_to_conversation_and_expires(tmp_path):
    storage = LocalAttachmentStorage(tmp_path)
    service = PublicConversationAttachmentService(storage)
    first = service.create(agent_id="agent-one", slug="one")
    second = service.create(agent_id="agent-one", slug="one")
    conversation_id = uuid.UUID(first["conversation_id"])
    uploaded = service.add_file(
        conversation_id=conversation_id,
        token=first["conversation_token"],
        agent_id="agent-one",
        slug="one",
        filename="note.txt",
        content_type="text/plain",
        data="这是只属于当前会话的资料".encode(),
    )
    file_id = uuid.UUID(uploaded["id"])
    context = service.context_for_message(
        conversation_id=conversation_id,
        token=first["conversation_token"],
        agent_id="agent-one",
        slug="one",
        file_ids=[file_id],
    )
    assert "这是只属于当前会话的资料" in context
    assert uploaded["name"] in context
    assert not list(tmp_path.glob("**/*.pdf"))

    with pytest.raises(ValidationException):
        service.context_for_message(
            conversation_id=conversation_id,
            token=second["conversation_token"],
            agent_id="agent-one",
            slug="one",
            file_ids=[file_id],
        )
    with pytest.raises(ValidationException):
        service.context_for_message(
            conversation_id=conversation_id,
            token=first["conversation_token"],
            agent_id="agent-two",
            slug="two",
            file_ids=[file_id],
        )

    metadata = json.loads(storage.read(f"{conversation_id}/meta.json"))
    metadata["expires_at"] = time.time() - 1
    storage.write(f"{conversation_id}/meta.json", json.dumps(metadata).encode())
    with pytest.raises(ValidationException):
        service.context_for_message(
            conversation_id=conversation_id,
            token=first["conversation_token"],
            agent_id="agent-one",
            slug="one",
            file_ids=[file_id],
        )
