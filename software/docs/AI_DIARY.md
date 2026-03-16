# AI Build Diary

## 2026-03-16 - Day 1 Product Assembly Milestone

This morning started with a practical homeowner problem: how to integrate HVAC behavior more intelligently with a new home solar system, without being boxed in by the limitations of commercial products. That led to a brainstorming session in ChatGPT around existing options such as Sensibo, where they fall short, and what a more flexible system might look like if it were designed from first principles.

Very quickly, that stopped being a vague idea and became a product concept. The ChatGPT phase helped collapse uncertainty fast: bill-of-materials planning, hardware tradeoffs, enclosure dimensions, measurement capture, and the rough path from concept to a printer-ready case model all came together quickly enough that turnkey hardware could be ordered for next-day delivery with real confidence.

That is an important part of the story because SmartBlaster was never just an app. Even on Day 1, the work already spanned hardware design and repo structure for electronics, enclosure work, and mechanical specifications, alongside assembly and wiring documentation. The physical side had enough definition to move from speculation to procurement.

Once the hardware was in motion, the work shifted into VS Code so the shipping time could be turned into implementation time. That handoff was the second half of the day: ChatGPT helped shape the physical product and validate that it was viable; GitHub Copilot in VS Code then helped turn the waiting window into a serious software sprint.

By the end of that sprint, SmartBlaster had gone from a blank slate to a working hybrid hardware/software product. The software side produced:
- A captive-portal provisioning flow that works from a phone browser
- Runtime failover back into setup mode when network connectivity is lost
- Unattended recovery from temporary network outages
- Primitive GitHub-based app updates
- Versioned setup-state persistence with migration hooks
- Owner-facing documentation for setup and operation
- An automated test suite covering provisioning, bootstrap, migration, and update paths

What makes the result satisfying is the breadth. In one day, the work covered software runtime, provisioning UX, update and recovery logic, documentation, tests, and the hardware groundwork needed to turn arriving parts into a real device rather than a slide-deck prototype.

Some Day 1 numbers are worth preserving:
- The working tree at this point spans 42 Python source files, 25 test files, and 2 markdown docs under `src`, `tests`, and `docs`.
- Those source, test, and doc files add up to 6,332 total lines.
- The setup portal now exposes 13 HTTP endpoints, covering setup, camera tools, device metadata, updates, reboot, and docs.
- The automated test suite already contains 99 explicit pytest test functions.
- The software stack pulls together 7 runtime libraries, plus 2 dev/test dependencies and 2 build-time packaging tools.
- Outside the software tree, the full SmartBlaster repo already carries dedicated hardware areas for electronics, enclosure design, and mechanical specifications, plus assembly and wiring documentation.

The practical outcome is already meaningful. This is good enough to pack in a suitcase, carry to a house, provision with only a phone, and use to gather real-world command-validation and reference-image data.

Tomorrow's practical milestone is even better: thanks to overnight delivery, nearly all reference hardware should be in hand and ready for first deployment testing.

The point of this diary is not hype. It is to keep a factual record of how AI-assisted engineering moved from a homeowner problem, to a validated design concept, to hardware on order, to a fairly complete first software implementation in roughly a day.
