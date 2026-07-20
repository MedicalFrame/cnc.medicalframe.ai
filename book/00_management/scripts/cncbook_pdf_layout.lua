local function is_standalone_image(block)
  return (block.t == "Para" or block.t == "Plain")
    and #block.content == 1
    and block.content[1].t == "Image"
end

local function caption_inlines(block)
  if (block.t ~= "Para" and block.t ~= "Plain") or #block.content ~= 1 then
    return nil
  end
  if block.content[1].t ~= "Emph" then
    return nil
  end
  return block.content[1].content
end

local function bind_images_to_captions(blocks)
  local output = {}
  local index = 1

  while index <= #blocks do
    local image_block = blocks[index]
    local caption_block = blocks[index + 1]
    local caption = caption_block and caption_inlines(caption_block) or nil

    if is_standalone_image(image_block) and caption then
      output[#output + 1] = pandoc.Figure(
        {pandoc.Plain({image_block.content[1]})},
        pandoc.Caption({pandoc.Plain(caption)}),
        pandoc.Attr("", {"cnc-figure"})
      )
      index = index + 2
    else
      output[#output + 1] = image_block
      index = index + 1
    end
  end

  return output
end

local function style_section_break()
  if FORMAT:match("latex") or FORMAT:match("beamer") then
    return pandoc.RawBlock("tex", "\\cncsectionbreak")
  end
  return nil
end

return {
  {Blocks = bind_images_to_captions},
  {HorizontalRule = style_section_break},
}
