"""Section 14.1 of the specification, as code.

A core document has one canonical serialization, so that two tools producing
the same publication produce the same bytes. Reference implementation: the
corpus is written in this form, and tests/test_canonical.py holds it to it.

Attribute order is not decided here. Section 14.1 gives it, element by
element, and this serializer keeps the order it is handed: it says how a
document is laid out, not what its author put in it.
"""

import io
import sys
from xml.etree import ElementTree

XML_NAMESPACE = "http://www.w3.org/XML/1998/namespace"
DECLARATION = '<?xml version="1.0" encoding="UTF-8"?>'
INDENT = "  "


def read(data):
    """Parses a core document into its root element and root declarations.

    The declarations map a URI to the prefix it was declared under, the empty
    string standing for the default namespace.
    """
    prefixes = {}

    # Only what the root declares: a declaration further down belongs to the
    # foreign content that carries it, and writing it on the root would
    # change what the document means.
    for event, payload in ElementTree.iterparse(io.BytesIO(data), ["start-ns", "start"]):
        if event == "start":
            break

        prefix, uri = payload
        prefixes[uri] = prefix

    return ElementTree.fromstring(data), prefixes


def serialize(root, prefixes):
    """The document with `root` as its root element, as bytes."""
    lines = [DECLARATION]
    default = next((uri for uri, prefix in prefixes.items() if prefix == ""), None)
    _write(root, 0, prefixes, default, lines, is_root=True)
    return ("\n".join(lines) + "\n").encode("utf-8")


def _write(element, depth, prefixes, default, lines, is_root=False):
    declarations, default = _declarations(element, prefixes, default, is_root)
    name = _name(element.tag, prefixes, default)
    start = name + declarations + _attributes(element, prefixes)
    children = list(element)
    text = (element.text or "").strip()
    pad = INDENT * depth

    if not children and not text:
        lines.append(f"{pad}<{start}/>")
        return

    # An element carrying Normalized text keeps it on the element's own line:
    # section 14.1 admits no insignificant whitespace inside it.
    if not children:
        lines.append(f"{pad}<{start}>{_escape(text)}</{name}>")
        return

    lines.append(f"{pad}<{start}>")

    for child in children:
        _write(child, depth + 1, prefixes, default, lines)

    lines.append(f"{pad}</{name}>")


def _declarations(element, prefixes, default, is_root):
    """What this element declares, and the default namespace below it.

    The root carries every declaration of the document. Below it, only
    foreign content in Extensions declares anything: its own namespace, or
    the absence of one where a default namespace is in scope.
    """
    if is_root:
        return "".join(_declaration(prefix, uri) for uri, prefix in prefixes.items()), default

    uri = _uri(element.tag)

    if uri == default or uri in prefixes or uri == XML_NAMESPACE:
        return "", default

    # An element in no namespace under a default namespace has to say so,
    # or it would be read as belonging to that namespace.
    return _declaration("", uri or ""), uri


def _declaration(prefix, uri):
    return f' xmlns="{_escape_attribute(uri)}"' if prefix == "" else f' xmlns:{prefix}="{_escape_attribute(uri)}"'


def _attributes(element, prefixes):
    return "".join(f' {_attribute_name(name, prefixes)}="{_escape_attribute(value)}"'
                   for name, value in element.attrib.items())


def _name(tag, prefixes, default):
    uri = _uri(tag)
    local = tag.rsplit("}", 1)[-1]

    if uri is None or uri == default:
        return local
    if uri == XML_NAMESPACE:
        return f"xml:{local}"

    prefix = prefixes.get(uri)

    # Foreign content the root does not declare is written under the default
    # namespace it declares for itself.
    return local if prefix in (None, "") else f"{prefix}:{local}"


def _attribute_name(name, prefixes):
    uri = _uri(name)

    if uri is None:
        return name
    if uri == XML_NAMESPACE:
        return f"xml:{name.rsplit('}', 1)[-1]}"

    prefix = prefixes.get(uri)

    # An unprefixed attribute is in no namespace, so a namespaced one needs
    # the prefix its declaration gave it.
    if not prefix:
        raise ValueError(f"{name} is in a namespace with no prefix to write it under.")

    return f"{prefix}:{name.rsplit('}', 1)[-1]}"


def _uri(name):
    return name[1:].split("}", 1)[0] if name.startswith("{") else None


def _escape(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _escape_attribute(value):
    return _escape(value).replace('"', "&quot;")


if __name__ == "__main__":
    root, namespaces = read(sys.stdin.buffer.read())
    sys.stdout.buffer.write(serialize(root, namespaces))
