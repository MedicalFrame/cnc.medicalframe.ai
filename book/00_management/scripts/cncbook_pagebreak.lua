function RawBlock(el)
  if el.format ~= "tex" or not el.text:match("\\newpage") then
    return nil
  end

  if FORMAT:match("latex") or FORMAT:match("beamer") then
    return el
  end

  if FORMAT:match("docx") then
    return pandoc.RawBlock("openxml", '<w:p><w:r><w:br w:type="page"/></w:r></w:p>')
  end

  if FORMAT:match("html") or FORMAT:match("epub") then
    return pandoc.RawBlock("html", '<div style="page-break-after: always;"></div>')
  end

  return nil
end
