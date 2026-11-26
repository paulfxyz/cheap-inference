# cheap-inference 2.0.0 social kit

Everything to announce the release on X, LinkedIn and Product Hunt. All posts are published by hand.

```
kit/
├── x-thread.md                 5-post thread, alt text, optional hook line
├── linkedin.md                 main post + 2 comments, alt text
├── producthunt/
│   ├── producthunt.md          name, tagline, description, topics, first comment, reply starters
│   ├── thumbnail-240.gif       240x240 animated thumbnail
│   └── gallery-*.png           four 1270x760 gallery images
├── video/
│   ├── cheap-inference-cover.mp4          1280x720, 14 s, no audio
│   ├── cheap-inference-cover-silent.mp4   same, for platforms that strip audio
│   └── cover-1280x720.png                 still frame
├── icons/                      5 animated icons, GIF at 512 and 240 px
│                               funnel, linter, ladder, cache, budget
├── svg/                        4 animated SVGs (hero, linter, ladder, context diet)
└── gen.py                      regenerates icons, video and gallery from code
```

## Suggested order

1. Product Hunt page live (or scheduled).
2. X thread: video on post 1, icon GIFs on posts 2 to 5.
3. LinkedIn main post with the video, then comment 1 (link) and comment 2 (receipts).

## Checks done

- Every claim in the copy matches the repository: 13 tools, 42 prompts, 100 tips, 14 chapters, 10 recipes, 30 tests, MIT.
- No author is named and no outside post is linked.
- Counts of characters: tagline within 60, short description within 260.

Notes: the GIFs are generated frames (no audio). The GOPOLO hook is optional and only appears as a marked line; remove it if you do not want it.
