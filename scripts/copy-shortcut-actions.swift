import AppKit
import Foundation

guard CommandLine.arguments.count == 2 else {
    fputs("usage: copy-shortcut-actions <actions-or-workflow.plist>\n", stderr)
    exit(64)
}

let sourceURL = URL(fileURLWithPath: CommandLine.arguments[1])
let sourceData = try Data(contentsOf: sourceURL)
let propertyList = try PropertyListSerialization.propertyList(
    from: sourceData,
    options: [],
    format: nil
)

let actions: [[String: Any]]
if let actionList = propertyList as? [[String: Any]] {
    actions = actionList
} else if
    let workflow = propertyList as? [String: Any],
    let workflowActions = workflow["WFWorkflowActions"] as? [[String: Any]]
{
    actions = workflowActions
} else {
    fputs("plist has no Shortcuts action array\n", stderr)
    exit(65)
}

guard !actions.isEmpty else {
    fputs("Shortcuts action array is empty\n", stderr)
    exit(65)
}

let actionType = NSPasteboard.PasteboardType("com.apple.shortcuts.action")
let items: [NSPasteboardItem] = try actions.map { action in
    let data = try PropertyListSerialization.data(
        fromPropertyList: action,
        format: .binary,
        options: 0
    )
    let item = NSPasteboardItem()
    guard item.setData(data, forType: actionType) else {
        throw NSError(
            domain: "ShortcutPasteboard",
            code: 1,
            userInfo: [NSLocalizedDescriptionKey: "failed to create action pasteboard item"]
        )
    }
    return item
}

let pasteboard = NSPasteboard.general
pasteboard.clearContents()
guard pasteboard.writeObjects(items) else {
    fputs("failed to write actions to the general pasteboard\n", stderr)
    exit(66)
}

guard
    let storedItems = pasteboard.pasteboardItems,
    storedItems.count == items.count,
    storedItems.allSatisfy({ $0.data(forType: actionType) != nil })
else {
    fputs("clipboard verification failed\n", stderr)
    exit(67)
}

print("Copied and verified \(items.count) Shortcuts actions on the clipboard.")
