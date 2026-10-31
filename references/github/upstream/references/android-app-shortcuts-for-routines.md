# Android Automation Hooks: App Shortcuts for Samsung Modes & Routines

Which app actions a phone's automation surface can invoke is decided by ONE
platform mechanism, and it differs between the two directions of a routine.

## The two directions — only one needs app cooperation

| Routine direction | What it does | App-side requirement |
|:--|:--|:--|
| **Trigger** ("If … app opened") | system watches the foreground package | **none** — any installed app is selectable |
| **Action** ("Then … open app") | enumerates the app's registered **App Shortcuts** | shortcuts MUST be registered by the app |

So "my app doesn't appear in Routines' action list" is always a missing-shortcut
problem, never a permission or OEM-adaptation problem. Third-party tools
(Tasker, MacroDroid) bypass this by firing raw intents/broadcasts with
`am broadcast` — useful as a stopgap, but the native routine cannot do that.

## Two registration routes

### Static (`res/xml/shortcuts.xml`) — fixed action set

```xml
<shortcuts xmlns:android="http://schemas.android.com/apk/res/android">
  <shortcut android:shortcutId="toggle_proxy" android:enabled="true"
      android:icon="@drawable/ic_toggle"
      android:shortcutShortLabel="@string/sc_toggle">
    <intent android:action="PKG.action.TOGGLE"
        android:targetPackage="PKG"
        android:targetClass="PKG.ShortcutActivity"/>
  </shortcut>
</shortcuts>
```

Plus on the launcher activity:

```xml
<meta-data android:name="android.app.shortcuts"
           android:resource="@xml/shortcuts" />
```

Use when the action set is closed (start / stop / toggle). Zero runtime cost,
visible immediately after install.

### Dynamic (`ShortcutManagerCompat.setDynamicShortcuts`) — runtime-varying set

Required when the list depends on user data (profiles, named configs). Costs:
must be re-registered every app start (and on locale change, since labels are
localised), and One UI refreshes its routine picker lazily. Cap is ~5 per app.
Registration alone is not enough for state-derived lists: add a listener that
re-registers whenever the underlying list changes (import/delete/rename),
otherwise the set stays stale until the next cold start — and force-stop +
relaunch does NOT fix staleness caused by items written after the last boot's
persist point.

Both surfaces read the same registry, but **the launcher long-press popup is
NOT a reliable check**: MIUI (and some other launchers) render only the first
few dynamic shortcuts, so six registered ids can display as four. The
authoritative check from a debuggable host is
`adb shell dumpsys shortcut` filtered to your package — count entries there,
not on screen. Modes & Routines / Tasker enumerate the service registry, so a
short UI menu is expected behaviour, not a defect.

## The half-wired trap

Apps sometimes ship `reportShortcutUsed(ctx, "toggle")` (a usage-report call)
while the shortcut itself is only ever registered dynamically at runtime — so a
manifest scan says "no shortcuts exist" while the code clearly references one.
Before concluding a feature is missing, grep the whole tree for the shortcut id
and read who calls the registration function (usually an init path like
`initShortcuts()` invoked from app bootstrap and locale listeners).

## Adding a new ACTION to an app whose state lives in Flutter/Dart

Service start/stop state machines often live in the Kotlin layer, but business
state (proxy mode, selected profile) lives in the Dart layer behind Riverpod.
A new intent action therefore cannot act directly — it must cross the existing
MethodChannel bridge:

```
Intent (Kotlin receiver/activity)
  → plugin object held in a global state holder
    → channel.invokeMethod("changeMode", key)
      → Dart handler: controller.changeMode(Enum.fromString(key)); savePreferences()
```

Find the app's non-UI entry points first: desktop-tray handlers do exactly this
already (tray → provider action without opening a window) — copy that path
rather than inventing one. Persist preferences in the handler, or the change
 evaporates on next start.

Semantics to pin down before coding: changing mode/profile should require the
service running and must NOT implicitly start/stop it — keep toggling and
configuration orthogonal so routines compose.

## Why toggle-only apps fail automations

A single TOGGLE action makes routine outcomes nondeterministic: if a trigger
can fire both on success and failure paths, callers cannot know the resulting
state. Expose explicit START and STOP alongside TOGGLE so every routine names
the state it wants. This is the argument to make (to upstream or internally)
when an app ships toggle-only shortcuts.
