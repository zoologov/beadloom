# BDL-076 (`beadloom-ujzb.12`). A project's own text, shown on its portal as it was written.
#
# VitePress compiles every Markdown page as a Vue template. The generator copies
# the project's own text onto portal pages: the README onto the About page, the
# first paragraph of the README onto the root service's page, and every document
# under `docs/` into the published documentation. Measured on VitePress 1.6.4:
# a Helm value `{{ .Values.image.tag }}` in that text failed `vitepress build`,
# `{{ name }}` rendered as nothing and `{{ 1 + 1 }}` rendered as `2`, both in
# prose and in inline code; an unclosed `<details>` and `List<String>` failed the
# build; a raw `<img>` of a missing file failed it too; and a raw `<a href>` to
# a repository file built but led nowhere.
#
# On the portal, the project's text is the author's text rather than a template.
# An interpolation is shown with its braces apart (an empty comment between them,
# which renders nothing) or inside an element Vue skips (`v-pre`), a tag Vue
# cannot compile shows as the text it is, and a raw link follows the rule every
# Markdown link in project text follows.

@bead:beadloom-ujzb.12 @node:site-generation
Feature: a project's own text is shown as written, never compiled as a Vue template

  Scenario: a Helm value in the README reaches the About page and the root service's page as text
    Given a project whose README opens with "Set {{ .Values.image.tag }} or `{{ .Values.image.tag }}` in values."
    When the project is initialised and its site is generated
    Then the About page holds "{{ .Values.image.tag }}" twice, each where Vue does not read it
    And the root service's page holds "{{ .Values.image.tag }}" twice, each where Vue does not read it

  Scenario: a tag Vue cannot compile shows as the text it is
    Given a project whose README opens with "Takes orders."
    And the project's document "docs/guide.md" reads "Returns List<String> items.\n\n<details><summary>More</summary>\n\nHidden."
    When the project is initialised and its site is generated
    Then the published guide shows "<String>" as text
    And the published guide shows "<details>" as text
    And the published guide keeps "<summary>More</summary>" as HTML

  Scenario: a raw link and a raw image follow the rule every link in project text follows
    Given a project whose README opens with "Takes orders."
    And the project declares the repository "https://gitlab.com/acme/orders"
    And the project's document "docs/guide.md" reads "<a href=\"../LICENSE\">license</a> and <img src=\"missing.png\" alt=\"a diagram\">"
    And the project is committed to git
    When the project is initialised and its site is generated
    Then the published guide links "license" in HTML to "https://gitlab.com/acme/orders/-/blob/{commit}/LICENSE"
    And the published guide reads "a diagram" in place of the image

  # BDL-076 (`beadloom-ujzb.21`). The text is read the way VitePress's markdown-it
  # reads it: four columns past a list item's content, or after a quote's marker,
  # is code markdown-it renders without `v-pre`.
  @bead:beadloom-ujzb.21
  Scenario: a Helm value in indented code inside a list item and a quote reaches no Vue template
    Given a project whose README opens with "Takes orders."
    And the project's document "docs/guide.md" reads "- install:\n\n      helm install {{ .Release.Name }}\n\n> Then:\n>\n>     helm upgrade {{ .Release.Name }}"
    When the project is initialised and its site is generated
    Then the published guide holds "{{ .Release.Name }}" in 2 blocks Vue skips

  @bead:beadloom-ujzb.21
  Scenario: a generic type and a Vue event inside raw HTML do not reach Vue as template
    Given a project whose README opens with "Takes orders."
    And the project's document "docs/guide.md" reads "<details>\n<summary>Map<String, Integer> config</summary>\n\nBody.\n\n</details>\n\n<div @click=\"go\">hi</div>"
    When the project is initialised and its site is generated
    Then the published guide shows "<String," as text
    And the published guide keeps "<summary>" as HTML
    And the published guide holds no "@click"
