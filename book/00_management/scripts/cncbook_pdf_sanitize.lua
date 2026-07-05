local replacements = {
  ["😊"] = "[웃는 이모지]",
}

function Str(el)
  for source, replacement in pairs(replacements) do
    el.text = el.text:gsub(source, replacement)
  end
  return el
end
