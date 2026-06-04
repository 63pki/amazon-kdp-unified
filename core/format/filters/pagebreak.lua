--[[
pagebreak – convert raw LaTeX page breaks to other formats

Based on the pandoc-ext/pagebreak filter.
Copyright © 2017-2021 Benct Philip Jonsson, Albert Krewinkel
License: ISC
]]

local stringify_orig = (require 'pandoc.utils').stringify

local function stringify(x)
  return type(x) == 'string' and x or stringify_orig(x)
end

local pagebreak = {
  epub = '<p style="page-break-after: always;"> </p>',
  html = '<div style="page-break-after: always;"></div>',
  latex = '\\newpage{}',
  ooxml = '<w:p><w:r><w:br w:type="page"/></w:r></w:p>',
}

local function newpage(format)
  if format:match 'epub' then
    return pandoc.RawBlock('html', pagebreak.epub)
  elseif format:match 'html.*' then
    return pandoc.RawBlock('html', pagebreak.html)
  elseif format:match 'latex' then
    return pandoc.RawBlock('tex', pagebreak.latex)
  elseif format == 'docx' then
    return pandoc.RawBlock('openxml', pagebreak.ooxml)
  else
    return pandoc.Para{pandoc.Str '\f'}
  end
end

local function is_newpage_command(command)
  return command:match '^\\newpage%{?%}?$'
    or command:match '^\\pagebreak%{?%}?$'
end

function RawBlock (el)
  if FORMAT:match 'tex$' then
    return nil
  end
  if el.format:match 'tex' and is_newpage_command(el.text) then
    return newpage(FORMAT)
  end
  return nil
end

function Para (el)
  if #el.content == 1 and el.content[1].text == '\f' then
    return newpage(FORMAT)
  end
end

return {
  {RawBlock = RawBlock, Para = Para}
}