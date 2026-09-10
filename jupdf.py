import nbformat
import base64
from pathlib import Path
import re
import sys

class FileWriter:
    def __init__(self, filepath):
        self.filepath = filepath

    def create(self):
        self.filepath.touch(exist_ok=True)

    def clear(self):
        self.filepath.write_text("", encoding="utf-8")

    def append(self, content):
        with self.filepath.open("a", encoding="utf-8") as file:
            file.write(content + "\n")

    def exists(self):
        return self.filepath.exists()

class TypstStringUtils:
    @staticmethod
    def setup(title):
        return \
"""#set document(title: ["""+title+"""])
#set page(paper: "a4", footer: context {
  if counter(page).get().first() != 1 [
    #set align(right)
    #strong(document.title)
    #datetime.today().display("[year]-[month]-[day]")
    #h(1fr)
    #counter(page).display(
      "1 of 1",
      both: true,
    )
  ]
})

#set par(
  justify: true,
)

#set heading(numbering: "1.")
#show heading.where(level: 1): it => [#it.body\\ ]
#show heading: smallcaps

#align(left + horizon)[
  #line(length: 100%, stroke: 1pt + gray)
  #show text: smallcaps
  #text(
    size: 36pt,
    weight: "bold",
  )[#context document.title]\\
  #text(fill: gray, datetime.today().display("[year]-[month]-[day]"))
  #line(length: 100%, stroke: 1pt + gray)
]

#pagebreak()

#show raw: block.with(
  width: 100%,
  stroke: luma(240) + 1pt,
  inset: (y: 3pt),
  radius: 4pt,
  clip: true,
)

#show raw.line: it => {
  let line_color = {
    if calc.even(it.number) {
      luma(245)
    } else {
      white
    }
  }
  box(fill: line_color, inset: (left: 5pt), outset: 3pt, width: 100%, {
    box(width: 2em, align(left)[#text(fill: blue, [#it.number])])
    it.body
  })
}
        """

    @staticmethod
    def codeblock(text, lang= "py"):
        return f'```py\n{text}\n```'

    @staticmethod
    def markdown(markdown: str) -> str:
        text = markdown

        # Headings
        text = re.sub(
            r"^(#{1,6})[ \t]+(.+)$",
            lambda m: "=" * len(m.group(1)) + " " + m.group(2),
            text,
            flags=re.MULTILINE,
        )

        # Strong: **text** -> #strong[text]
        text = re.sub(
            r"\*\*(.+?)\*\*",
            r"#strong[\1]",
            text,
        )

        # Italic: *text* -> #emph[text]
        text = re.sub(
            r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)",
            r"#emph[\1]",
            text,
        )

        # Numbered lists: 1. text -> + text
        text = re.sub(
            r"^\s*\d+\.[ \t]+(.+)$",
            r"+ \1",
            text,
            flags=re.MULTILINE,
        )

        # Unordered lists: - text -> - text
        # This is technically unchanged, but included for completeness.
        text = re.sub(
            r"^\s*-[ \t]+(.+)$",
            r"- \1",
            text,
            flags=re.MULTILINE,
        )

        return text


    @staticmethod
    def image(file):
        return f'#figure(\n\timage("{file}"),\n\tcaption: []\n)'

    @staticmethod
    def result(text):
        return f'#block(fill: luma(60), inset: 10pt, width: 100%, radius: 4pt)[\n\t#text(fill: luma(240))[*Output*]\\ #text(fill: luma(150))[{text}]\n]'


if __name__ == "__main__":
    input_name = sys.argv[1]

    print(f"Creating {input_name}...")

    input = Path(input_name)
    basedir = input.parent

    document = FileWriter(Path(input.stem + ".typ"))
    document.create()
    document.clear()

    with open(input, "r", encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)

        document.append(TypstStringUtils.setup(input.stem))

        for cell in nb.cells:
            print("\t" + cell.cell_type)
            # ----------------------------------- Code ----------------------------------- #
            if cell.cell_type == "code":
                document.append(TypstStringUtils.codeblock(cell.source))
                for output in cell.outputs:
                    if output.output_type == "display_data":

                        for mime_type, data in output.data.items():
                            if mime_type != "image/png" and mime_type != "image/jpg":
                                continue
                            
                            image_name = f"{cell.metadata.outputId}"
                            image_path = basedir.joinpath(str(image_name + "." + mime_type.split("/")[-1]))

                            image_data = base64.b64decode(data)
                            with open(image_path, "wb") as f:
                                f.write(image_data)
                            document.append(TypstStringUtils.image(str(image_path)))

                    elif output.output_type == "execute_result":
                        document.append(TypstStringUtils.result(output.data))
                    elif output.output_type == "stream":
                        document.append(TypstStringUtils.result(output.text))
            # --------------------------------- Markdown --------------------------------- #
            elif cell.cell_type == "markdown":
                document.append(TypstStringUtils.markdown(cell.source))

    print(f"{document.filepath} was successfully created...")