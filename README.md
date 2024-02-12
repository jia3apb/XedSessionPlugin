# Xed session plugin


The plugin imitates notepad++ session save/restore behaviour

- The main window can be closed even if some of the tabs are unsaved.
- When the main window closes, the plugin preserves all unsaved and saved tabs, and restores them for the next session.
- If a tab was saved into a file and then modified, the plugin restores the modified/updated version of the tab.
- Empty tabs are not saved.