# Pastebin — User Guide

Pastebin is a scratchpad for text. You pick a password, you get a private space, and inside it you keep any number of titled text items — notes, snippets, links, a paragraph you want to finish on the other machine. It does one thing, and the one thing it does not do is share: there is no public link, no share button, no URL you can hand to a colleague. The only way into your space is the password.

---

## 1. Getting started

1. Open the site. The landing page has two forms and a **?** button that explains the model in four sentences.
2. Under **Create new pastebin**, type a password twice and press **Create**. Minimum six characters, and no other rule.
3. You land on your dashboard, empty. Press **+ New** to write your first item.
4. Next time — same site, any device — type that password under **Open existing** and press **Open**.

There is no registration form, no email, no confirmation link, and no profile page. Pastebin does not use Borant ID: it has its own login, because an account here is not a person, it is a password.

A session cookie keeps you signed in for **30 days** per browser, so you type the password once per device and not once per visit. **Sign out** clears it. On a shared or lab machine, sign out when you leave — the cookie outlives the browser window.

## 2. The password is the account

This is the one thing worth reading twice, because everything else follows from it.

There are **no usernames**. Pastebin looks you up by your password alone, which has two consequences that no other password you use has:

- **Passwords are unique across the whole instance.** If you try to create a pastebin with a password someone else already picked, you are told the password is taken and invited to log in instead — which also tells you that a pastebin with that password exists. That cannot be hidden: two accounts cannot share one password, so you have to be told to pick another. What it costs to exploit is time, because attempts are throttled (§6).
- **Anyone who types your password is you.** Not "gets access to your account" — *is* your account. They see your items, edit them, delete them, and nothing distinguishes them from you, because there is nothing else to distinguish.

So a short, obvious or reused password is not a weak lock, it is an open door: someone who tries `password1` out of curiosity does not get an error, they get whoever's pastebin that is. Use a long random string from your password manager, and store it there before you press Create.

**There is no recovery.** No email, no reset link, no security question — lose the password and the items are unreachable, by design and not by omission. There is also **no way to change your own password**: only an administrator can reset one, and the honest workaround is to create a second pastebin with a better password and copy your items across by hand.

## 3. Items

An **item** is a title plus a body of free text. The title is required and is what you see on the card; the body may be left empty.

- **Create** — **+ New**, type a title and text, **Save**. `Ctrl+S` (`Cmd+S` on a Mac) saves while you are editing.
- **Read** — click a card. It opens in a viewer showing the full text, with line breaks preserved.
- **Edit** — **Edit** in the viewer, change anything, **Save**. `Escape` closes the window; **Cancel** drops your changes.
- **Delete** — **Delete**, then confirm. The item is removed immediately and permanently; there is no trash and no undo.

The dashboard is a grid of cards sorted by **last modified**, newest first, each showing the title, the first 120 characters of the text and the date it last changed. Every item you own is on that one page.

Text is stored and shown exactly as you typed it. There is no Markdown rendering, no syntax highlighting, no line numbers and no word wrap setting — it is a text box, and a code snippet comes back out identical to what went in.

## 4. What Pastebin does not do

Stated plainly, because a tool called "pastebin" invites assumptions that do not hold here:

- **No sharing.** No public links, no read-only URLs, no expiring links, no collaborators. Nothing you store is reachable by anyone who does not have your password.
- **No file upload.** Text only. A PDF, an image or a transcript file has nowhere to go — paste the text or use proper storage.
- **No expiry.** Items do not self-destruct after a day or a view. They stay until you delete them, which means an old paste is still there in a year unless you go and remove it.
- **No search, tags or folders.** One flat grid. If you keep dozens of items, put the distinguishing word in the title, because the title is all you have to navigate by.
- **No history.** Saving overwrites; the previous version of the text is gone.
- **No account deletion.** You can empty your pastebin by deleting every item, but the account itself has no delete button.

## 5. The administrator side

An instance may run with an administrator account. If one exists, this is exactly what it can see and do:

- A table of every pastebin: its number, the date it was created, the date of its last activity, and how many items it holds.
- **Not your password.** It is not stored in a readable form: the database holds an index that finds your row and a bcrypt hash that checks it, and neither can be turned back into what you typed. The administrator can set a new password for you, and cannot learn the old one.
- **Every item you have stored, in full** — a read-only view of your dashboard, titles and complete text.
- A password reset per pastebin, which is the only way back in for someone who has locked themselves out.

The administrator cannot edit or delete your items, and cannot delete your pastebin. Nothing here is a bug: it is a small self-hosted tool with a maintainer, and the maintainer can read it. Assume that.

## 6. Data protection

Pastebin has no protection to offer beyond one password, and one password is the whole of it. Before typing anything in, weigh the following.

- **Everything you store is readable by the administrator**, in the clear. Items are not encrypted at rest and there is no record of who read what, so nothing you put here is confidential from whoever runs the instance. Your password is the one thing that is not readable, by anyone, including them.
- **Login is protected by the password alone.** No second factor. Guesses are throttled — past eight failures in a minute from one address every answer is delayed by a second, past forty it is refused outright — which makes guessing slow rather than impossible. With one password namespace for the whole instance, a guessed password lands directly inside somebody's pastebin, so a long random password is not advice here but the security model.
- **Interview transcripts, participant data, health data and any other personal or special-category data should not go in at all.** Not pseudonymised, not "just for an hour" — the item has no expiry, so "just for an hour" becomes permanent by default. Use the institutional storage your data management plan names, and if your ethics approval mentions where data may live, this is not that place.
- **No credentials, API keys or tokens.** Items are stored unencrypted and visible to the administrator, and a secret in a scratchpad is a secret you no longer control.
- **Never the only copy.** Delete is immediate and irreversible, there is no version history, and there is no recovery path if the password is lost. Anything you would be sorry to lose lives somewhere with a backup, and Pastebin holds the working copy.
- Compliance with GDPR, the Swiss FADP and your institutional requirements is yours, not the tool's. When in doubt, ask your data protection officer before pasting, not after.

## 7. Good practices

- **Generate the password in your password manager and save it there first.** It is the only credential in the system and there is no way to recover it, so the two-minute version of this step is the entire security model working.
- Use it for what it is: **text in transit between your own machines**. A paragraph, a command, a reference, a draft — things whose loss would be annoying rather than expensive.
- **Titles do the work of search.** Write the title you would type into a search box you do not have.
- **Clear out what you no longer need**, because nothing expires and an unreviewed pastebin is a slow accumulation of things you have forgotten you left there.
- If you find yourself wanting to send someone a link to an item, that is the signal to use a different tool: Pastebin will not do it, and working around it means writing the password in a chat message, which hands over everything you have ever stored.
