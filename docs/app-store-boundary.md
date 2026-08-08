# Apple distribution boundary

This repository is a personal/internal prototype assembled from user-created
Shortcuts automation, iMessage, and a Mac service. It is not itself an iOS App
Store binary, and its existence does not imply that Apple would approve a native
app with the same implementation.

Apple documents personal Shortcuts automations and permits users to configure
some automations to run without asking. That supports this owner-operated setup:

- [Apple: Intro to personal automation](https://support.apple.com/guide/shortcuts/intro-to-personal-automation-apd690170742/ios)

An AiRA App Store product should use a narrower architecture:

- ship explicit, reviewable App Intents and actions in the app;
- use only public APIs for their intended purposes;
- ask immediately before calls, sends, purchases, uploads, or permission changes;
- clearly indicate and obtain consent for screen or input capture;
- treat remote model output as a proposed action, not executable downloaded code;
- avoid private app URL schemes, arbitrary Shortcut execution, screen scraping,
  or unrelated background execution;
- disclose every capability and the remote Mac/cloud dependency to App Review.

The relevant current rules include public-API use (2.5.1), self-contained code
(2.5.2), limited background services (2.5.4), expected Siri/Shortcuts intents
(2.5.11), explicit indication and consent for recording user activity (2.5.14),
and the restrictions on exposing native APIs to hosted software (4.7.2):

- [Apple App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)

The practical product line is: Apple is likely to review a transparent assistant
that proposes and invokes a finite set of declared actions; a covert general
remote-control layer built on private deep links is high rejection risk.
