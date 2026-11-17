from __future__ import annotations

import re
from typing import Any, Dict, List

from backend.models.schemas import IntentClassificationResult


class ToolNeedClassifier:
    """Retrieval-focused classifier.

    Tool need is intentionally not inferred here. The execution loop exposes
    policy-authorized tool schemas to the model and lets structured tool_calls
    drive tool use.
    """

    VERSION = "retrieval-only-v3"

    KB_REQUIRED_PATTERNS = [
        r"第\s*[一二三四五六七八九十百0-9]+\s*[条款项]",
        r"\barticle\s+[0-9]+\b",
        r"\bsection\s+[0-9]+\b",
    ]
    KB_REQUIRED_KEYWORDS = [
        "我上传的",
        "两份资料",
        "结合资料",
        "竞赛目录",
        "校规",
        "规定",
        "制度",
        "章程",
        "手册",
        "准则",
        "守则",
        "办法",
        "细则",
        "处分",
        "处罚",
        "请假流程",
        "申诉",
        "考勤",
        "旷课",
        "违纪",
        "奖惩",
        "文件里",
        "文档中",
        "知识库里",
        "根据资料",
        "依据上传内容",
    ]
    SMALLTALK = {"你好", "您好", "hi", "hello", "谢谢", "thanks", "在吗"}
    QUESTION_MARKERS = ("?", "？", "什么", "如何", "怎么", "吗")
    DOCUMENT_INVENTORY_PATTERNS = (
        r"(?:知识库|资料库).{0,16}(?:有哪些|都有什么|有什么|全部|完整).{0,8}(?:文件|文档|资料)",
        r"(?:列出|列一下|查看).{0,12}(?:知识库|资料库|文件|文档).{0,8}(?:清单|列表)?",
    )

    def classify(
        self,
        user_input: str,
        agent_config: Dict[str, Any] | None = None,
        tool_catalog_summary: List[str] | None = None,
    ) -> IntentClassificationResult:
        text = user_input.strip()
        lowered = text.lower()
        matched_rules: List[str] = []

        if any(re.search(pattern, text) for pattern in self.DOCUMENT_INVENTORY_PATTERNS):
            return IntentClassificationResult(
                intent_type="KB_REQUIRED",
                query_subtype="document_inventory",
                confidence=0.98,
                matched_rules=["structured_knowledge_document_inventory"],
                requires_citation=True,
                allow_direct_answer=False,
                requires_user_confirmation=False,
            )

        exact_clause = False
        for pattern in self.KB_REQUIRED_PATTERNS:
            if re.search(pattern, lowered, flags=re.IGNORECASE):
                exact_clause = True
                matched_rules.append(f"kb_required_pattern:{pattern}")
        if re.search(r"第\s*[一二三四五六七八九十百0-9]+\s*[章节]", text):
            matched_rules.append("kb_required_chapter_or_section")
        if re.search(r"(?:根据|依据).{0,16}(?:上传|知识库|文档|文件|资料)", text):
            matched_rules.append("kb_required_uploaded_source")
        for keyword in self.KB_REQUIRED_KEYWORDS:
            if keyword in text:
                matched_rules.append(f"kb_required_keyword:{keyword}")
        if matched_rules:
            return IntentClassificationResult(
                intent_type="KB_REQUIRED",
                query_subtype="exact_clause" if exact_clause else "policy_explanation",
                confidence=0.92,
                matched_rules=matched_rules,
                required_knowledge_domains=self._knowledge_domains(text),
                requires_citation=True,
                allow_direct_answer=False,
                requires_user_confirmation=False,
            )

        if lowered in self.SMALLTALK:
            return IntentClassificationResult(
                intent_type="DIRECT_CHAT",
                query_subtype="smalltalk",
                confidence=0.8,
                matched_rules=["fallback:short_smalltalk"],
                requires_citation=False,
                allow_direct_answer=True,
                requires_user_confirmation=False,
            )

        # An explicit tool or mutation command is not a knowledge question.
        # Keep tool authorization in the separate policy gate.
        named_tools = [name.rsplit("/", 1)[-1].lower() for name in (tool_catalog_summary or [])]
        explicit_tool = any(name and name in lowered for name in named_tools)
        mutation_command = bool(re.match(r"^(?:请|帮我|替我)?(?:删除|修改|创建|新建|发送|执行|调用)", text))
        if explicit_tool or mutation_command:
            return IntentClassificationResult(
                intent_type="DIRECT_CHAT",
                query_subtype="tool_operation",
                confidence=0.8,
                matched_rules=["explicit_tool_or_action"],
                requires_citation=False,
                allow_direct_answer=True,
                requires_user_confirmation=False,
            )

        # A document-backed agent may receive a topic or an imperative rather
        # than a question. Optional retrieval probes its own indexed sources;
        # evidence relevance is decided separately by the retrieval service.
        return IntentClassificationResult(
            intent_type="KB_OPTIONAL",
            query_subtype="fact_lookup",
            confidence=0.6,
            matched_rules=["fallback:optional_knowledge_probe"],
            requires_citation=False,
            allow_direct_answer=True,
            requires_user_confirmation=False,
        )

    @staticmethod
    def _knowledge_domains(text: str) -> List[str]:
        if "合同" in text:
            return ["contract"]
        if any(keyword in text for keyword in ("校规", "学生", "考勤", "处分", "请假", "旷课")):
            return ["school_rules"]
        return []


tool_need_classifier = ToolNeedClassifier()
