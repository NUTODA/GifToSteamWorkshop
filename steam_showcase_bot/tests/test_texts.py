from steam_showcase_bot import texts


def test_esc_escapes_html_entities():
    assert texts.esc('<b>&') == '&lt;b&gt;&amp;'


def test_status_text_escapes_filename_and_error():
    result = texts.status_text(
        filename='<demo>.mp4',
        step=texts.STEP_SCALE,
        failed_at=texts.STEP_SCALE,
        error_msg='<ошибка>',
    )

    assert '<code>&lt;demo&gt;.mp4</code>' in result
    assert '&lt;ошибка&gt;' in result
    assert '❌ <b>Ошибка при обработке</b>' in result
