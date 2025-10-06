from markdown_pdf.html_styles import apply_html_styles


def test_span_color_conversion():
    html = '<span style="color: #ff0000;">Important</span>'
    result = apply_html_styles(html)
    assert '\\textcolor[HTML]{FF0000}{Important}' in result


def test_div_alignment_and_background():
    html = '<div style="text-align: center; background-color: rgb(10, 20, 30);">Texte</div>'
    result = apply_html_styles(html)
    assert '\\begin{center}' in result
    assert '\\end{center}' in result
    assert '\\colorbox[HTML]{0A141E}' in result


def test_nested_styles():
    html = '<div style="text-align:right;"><span style="font-weight:bold;">Note</span></div>'
    result = apply_html_styles(html)
    assert '\\textbf{Note}' in result
    assert '\\begin{flushright}' in result
