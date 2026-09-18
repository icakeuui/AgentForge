from backend.services.tool_need_classifier import tool_need_classifier


def test_classifier_marks_smalltalk_as_direct_chat():
    result = tool_need_classifier.classify("你好")

    assert result.intent_type == "DIRECT_CHAT"
    assert result.query_subtype == "smalltalk"
    assert result.allow_direct_answer is True
    assert result.requires_citation is False


def test_classifier_marks_school_clause_as_required_exact_clause():
    result = tool_need_classifier.classify("校规第十条是")

    assert result.intent_type == "KB_REQUIRED"
    assert result.query_subtype == "exact_clause"
    assert result.requires_citation is True
    assert "school_rules" in result.required_knowledge_domains


def test_classifier_does_not_infer_destructive_tool_need():
    result = tool_need_classifier.classify("帮我删除全部文档")

    assert result.intent_type == "DIRECT_CHAT"
    assert result.requires_user_confirmation is False


def test_classifier_does_not_infer_websearch_tool_need():
    result = tool_need_classifier.classify("用 websearch 查 Cursor 最新文档", tool_catalog_summary=["builtin/websearch"])

    assert result.intent_type == "DIRECT_CHAT"
    assert result.candidate_tool_domains == []


def test_classifier_marks_short_question_as_kb_optional():
    result = tool_need_classifier.classify("学校纪律严格吗")

    assert result.intent_type == "KB_OPTIONAL"
    assert result.query_subtype == "fact_lookup"
