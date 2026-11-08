# How to publish PhoneKey Vault

This guide takes you from "files on my Desktop" to "public, dated and getting feedback" in about an hour, one site at a time. Every post you need is already written in this `launch` folder; you only paste and click.

## Read this first: going public is a one-way door

- **What you gain:** public, dated proof that *you* built this. A GitHub repository's history and a dated article are hard evidence of who had the idea first, and when.
- **What you give up:** in most countries, once an invention is public, you can no longer patent it. Software patents are hard to get anyway, and most student startups win by building faster, not by patenting. If patenting matters to you, talk to your university's innovation or IP office **before** posting.
- **Licence:** the project uses the MIT licence. Anyone can use the code, but they must keep your name on it. If you'd rather keep the code private and only publish the white paper, skip Step 1 and post the article alone.

## Step 1: GitHub (the home for everything)

Your Git username on this PC is `demi956`. If that's your GitHub account, use it. If you don't have an account yet, create one at github.com (it's free).

1. **Create the repository.** Sign in at github.com and click **+ → New repository**.
    - Name: `phonekey-vault`
    - Description: `Your phone is your PC's key. Encrypted backup with phone-approved restore, built for students on slow, expensive internet.`
    - Choose **Public**, and **don't** tick "Add a README" (you already have one).
2. **Upload with Git, so your dated history goes with it.** The `phonekey` folder is already a Git repository, with a first commit dated 8 November 2026. Open a terminal in `myfirstprototype\phonekey` and run the two commands below. The first time, a browser window asks you to sign in to GitHub.

    ```bash
    git remote add origin https://github.com/demi956/phonekey-vault.git
    ```

    ```bash
    git push -u origin main
    ```

    Don't drag the files into the website instead: that would replace your dated history with a new, undated upload.
3. **Add topics and a website.** On the repository page, click the ⚙ next to **About** and add these topics: `backup`, `encryption`, `restic`, `python`, `students`, `ghana`, `africa`, `privacy`, `open-source`.
4. **Turn on private vulnerability reporting.** Go to **Settings → Security → Private vulnerability reporting → Enable**. This makes `SECURITY.md` work.
5. **Pin it.** On your GitHub profile, click **Customize your pins** and pin `phonekey-vault`.

Your project link will be `https://github.com/demi956/phonekey-vault`. Use it in every post below.

## Step 2: post in this order (one or two a day)

| Order | Site | Why it fits | File to paste |
| --- | --- | --- | --- |
| 1 | **dev.to** (or Hashnode) | Dated, searchable article; friendly to student builders | `devto-article.md` |
| 2 | **Reddit**: r/selfhosted, then r/SideProject and r/opensource | r/selfhosted already loves restic; honest feedback | `reddit-posts.md` |
| 3 | **Hacker News**: "Show HN" | The biggest single source of developer attention; blunt technical feedback | `show-hn.md` |
| 4 | **LinkedIn** and **X** | Your network, lecturers, recruiters, Ghana tech scene | `social-posts.md` |
| 5 | **Local communities** | GDG Accra, your university's computer science club, MEST Africa events, hackathons | Share the dev.to link with a two-line intro |
| Later | **Product Hunt** | Best once there's a phone app non-developers can try; launching a command-line prototype there wastes your one big launch | — |

## Step 3: in the first 48 hours after each post

- **Reply to every comment,** especially the critical ones. On Hacker News, the security questions will come first; the white paper's threat model (section 4) answers most of them.
- **Track what matters:** GitHub stars, people saying "I'd use this", and anyone offering to help build the phone app. Write them in a simple notes file.
- **Don't argue; thank and note.** A good line is: "Good point. That's a known prototype limit (see SECURITY.md), and the native app fixes it."

## What counts as traction

Signs the idea is worth building:

- 50+ GitHub stars in the first month.
- 100+ waitlist or "I'd use this" responses. This matches the roadmap's first gate.
- At least one person offering to contribute code.
- A lecturer, university IT office or incubator asking to talk.

If none of that happens, it isn't wasted: you have a public, documented project for your CV and a clear list of what people wanted instead.
