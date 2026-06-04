--[[
scene_break – Replace horizontal rules with styled scene breaks.

For LaTeX output: centered scene break text.
For HTML/EPUB output: styled <hr> element.
]]

local scene_break_text = "* * *"

function Meta(meta)
  if meta['scene-break'] then
    scene_break_text = pandoc.utils.stringify(meta['scene-break'])
  end
end

function HorizontalRule()
  if FORMAT:match 'latex' then
    return pandoc.RawBlock('tex',
      '\\vspace{1em}\n\\begin{center}' .. scene_break_text .. '\\end{center}\n\\vspace{1em}'
    )
  elseif FORMAT:match 'html' or FORMAT:match 'epub' then
    return pandoc.RawBlock('html',
      '<div style="text-align: center; margin: 1.5em 0; letter-spacing: 0.5em;">' ..
      scene_break_text .. '</div>'
    )
  end
end

return {
  {Meta = Meta},
  {HorizontalRule = HorizontalRule}
}