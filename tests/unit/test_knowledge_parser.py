from backend.services.knowledge_parser import knowledge_parser


def test_parser_extracts_article_chunks_with_metadata():
    chunks = knowledge_parser.parse(
        title="学生管理规定",
        content="第一章 总则\n第十条 学生不得无故旷课。\n第十一条 学生应按时参加考试。",
    )

    assert [chunk.article_no for chunk in chunks] == ["10", "11"]
    assert chunks[0].chunk_type == "article"
    assert chunks[0].article_label == "第十条"
    assert chunks[0].section_path == ["学生管理规定", "第一章", "第十条"]


def test_article_number_normalization_variants():
    assert knowledge_parser.extract_article_no("校规第十条是") == "10"
    assert knowledge_parser.extract_article_no("校规第10条是") == "10"
    assert knowledge_parser.extract_article_no("校规第 10 条是") == "10"
    assert knowledge_parser.extract_article_no("article 10") == "10"


def test_parser_falls_back_to_plain_chunks_without_articles():
    chunks = knowledge_parser.parse(title="普通资料", content="这是一段普通知识内容。")

    assert len(chunks) == 1
    assert chunks[0].chunk_type == "plain"
    assert chunks[0].article_no is None
