"""
Adds a release to the Sparkle appcast.

Usage: appcast.py SIGN_UPDATE_OUTPUT INFO_PLIST APPCAST

SIGN_UPDATE_OUTPUT is the output of Sparkle's sign_update for the archive,
like `sparkle:edSignature="..." length="..."`. INFO_PLIST is the app's
Info.plist, which provides the minimum system version. APPCAST is updated in
place, and created if it doesn't exist.

The release is described by the VERSION, BUILD, COMMIT, COMMIT_LONG, and
DOWNLOAD_URL environment variables.

Based on dist/macos/update_appcast_tag.py from Ghostty (MIT license).
"""

import os
import plistlib
import shlex
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

SPARKLE = "http://www.andymatuschak.org/xml-namespaces/sparkle"
NS = {"sparkle": SPARKLE}
PUBDATE_FORMAT = "%a, %d %b %Y %H:%M:%S %z"
KEEP_ITEMS = 15

sign_update_path, info_plist_path, appcast_path = sys.argv[1:]
version = os.environ["VERSION"]
build = os.environ["BUILD"]
commit = os.environ["COMMIT"]
commit_long = os.environ["COMMIT_LONG"]
download_url = os.environ["DOWNLOAD_URL"]
with open(info_plist_path, "rb") as f:
    minimum_system_version = plistlib.load(f)["LSMinimumSystemVersion"]
now = datetime.now(timezone.utc)

with open(sign_update_path) as f:
    enclosure_attrs = dict(pair.split("=", 1) for pair in shlex.split(f.read()))
if set(enclosure_attrs) != {"sparkle:edSignature", "length"}:
    sys.exit(f"unexpected sign_update output: {enclosure_attrs}")

ET.register_namespace("sparkle", SPARKLE)
if os.path.exists(appcast_path):
    tree = ET.parse(appcast_path)
else:
    rss = ET.Element("rss", {"version": "2.0"})
    ET.SubElement(ET.SubElement(rss, "channel"), "title").text = "Ghostty ReleaseSafe"
    tree = ET.ElementTree(rss)
channel = tree.find("channel")

# Replace any previous item for the same build, since Sparkle reports
# invalid signatures if it picks a stale one.
for item in channel.findall("item"):
    if item.findtext("sparkle:version", namespaces=NS) == build:
        channel.remove(item)

items = sorted(
    channel.findall("item"),
    key=lambda item: datetime.strptime(item.findtext("pubDate"), PUBDATE_FORMAT),
)
for item in items[: max(0, len(items) - (KEEP_ITEMS - 1))]:
    channel.remove(item)

version_dash = version.replace(".", "-")
release_notes = f"https://ghostty.org/docs/install/release-notes/{version_dash}"

item = ET.SubElement(channel, "item")
ET.SubElement(item, "title").text = f"Ghostty {version} (ReleaseSafe)"
ET.SubElement(item, "pubDate").text = now.strftime(PUBDATE_FORMAT)
ET.SubElement(item, f"{{{SPARKLE}}}version").text = build
ET.SubElement(item, f"{{{SPARKLE}}}shortVersionString").text = version
ET.SubElement(item, f"{{{SPARKLE}}}minimumSystemVersion").text = minimum_system_version
ET.SubElement(item, f"{{{SPARKLE}}}fullReleaseNotesLink").text = release_notes
ET.SubElement(item, "description").text = f"""
<h1>Ghostty v{version} (ReleaseSafe)</h1>
<p>
Built with <code>-Doptimize=ReleaseSafe</code> from commit
<code><a href="https://github.com/ghostty-org/ghostty/commit/{commit_long}">{commit}</a></code>.
</p>
<p>
Release notes: <a href="{release_notes}">{release_notes}</a>
</p>
"""
enclosure = ET.SubElement(item, "enclosure")
enclosure.set("url", download_url)
enclosure.set("type", "application/octet-stream")
for key, value in enclosure_attrs.items():
    enclosure.set(f"{{{SPARKLE}}}edSignature" if key == "sparkle:edSignature" else key, value)

ET.indent(tree)
tree.write(appcast_path, xml_declaration=True, encoding="utf-8")
