# Urban Health website: photography brief

Four photographs complete the "Made for the people you love" section. The section stays hidden
until all four files exist, so the live site never shows an empty frame.

**Source:** commissioned shoot or licensed stock (Getty, Shutterstock, Adobe Stock). Keep the
licence and a signed model release for every person shown. No AI-generated people.

**Style:** real Indian families, natural daylight, unposed, warm but not saturated. No studio
backdrops, no visible brand logos, no medical gore. Faces of children only with parental release.

| File | Shape | Scene |
|---|---|---|
| `people/p1.webp` | wide, 3:2 | Three generations in a sunlit living room; the grandmother shows her grandchild something on a phone. |
| `people/p2.webp` | tall, 3:4 | A woman in her thirties checks her elderly father's medicine strip against a reminder on her phone, at a kitchen table. |
| `people/p3.webp` | tall, 3:4 | A uniformed lab technician at a home doorway, smiling, holding a sealed sample kit; shot from inside the home. |
| `people/p4.webp` | wide, 3:2 | A father holds his toddler at a clinic just after a vaccine, calm; paediatrician softly out of focus. |

**Delivery:** at least 2400 px on the long side. Export WebP at quality 80 and place the files in
`site/preview/people/`, then add `site/preview/people/ready.json` containing `{"ready": true}`.
The section appears only after that file exists. Preview the frames any time with `/preview?photos=draft`.
