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

    VERSION = "retrieval-only-v2"

    KB_REQUIRED_PATTERNS = [
        r"第\s*[一二三四五六七八九十百0-9]+\s*[条款章节项]",
        r"\barticle\s+[0-9]+\b",
        r"\bsection\s+[0-9]+\b",
    ]
    KB_REQUIRED_KEYWORDS = [
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

    def classify(
        self,
        user_input: str,
        agent_config: Dict[str, Any] | None = None,
        tool_catalog_summary: List[str] | None = None,
    ) -> IntentClassificationResult:
        text = user_input.strip()
        lowered = text.lower()
        matched_rules: List[str] = []

        exact_clause = False
        for pattern in self.KB_REQUIRED_PATTERNS:
            if re.search(pattern, lowered, flags=re.IGNORECASE):
                exact_clause = True
                matched_rules.append(f"kb_required_pattern:{pattern}")
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

        if lowered in self.SMALLTALK or (len(text) <= 12 and not any(marker in text for marker in self.QUESTION_MARKERS)):
            return IntentClassificationResult(
                intent_type="DIRECT_CHAT",
                query_subtype="smalltalk",
                confidence=0.8,
                matched_rules=["fallback:short_smalltalk"],
                requires_citation=False,
                allow_direct_answer=True,
                requires_user_confirmation=False,
            )

        if any(marker in text for marker in self.QUESTION_MARKERS):
            return IntentClassificationResult(
                intent_type="KB_OPTIONAL",
                query_subtype="fact_lookup",
                confidence=0.66,
                matched_rules=["fallback:question"],
                requires_citation=False,
                allow_direct_answer=True,
                requires_user_confirmation=False,
            )

        return IntentClassificationResult(
            intent_type="DIRECT_CHAT",
            query_subtype="smalltalk",
            confidence=0.6,
            matched_rules=["fallback:direct_chat"],
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
