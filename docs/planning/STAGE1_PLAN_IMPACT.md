# Stage 1 Plan Impact — 52 plans generated under the double-buffer math

Decision-support report only (doctor notification / re-approval timing). **No plans were regenerated or modified.**

- Old math (bug): per-meal target = TDEE x 0.85 x split -> meals totalled 72.25% of TDEE.
- Corrected math (`cf1b6ab`, `compute_meal_targets()`): per-meal target = TDEE x split -> meals total 85% of TDEE; 15% passive buffer applied exactly once.
- Targets below are computed from each patient's **current** profile (weight/activity at generation time may have differed slightly).
- "Dishes changed" comes from ONE in-memory regeneration per patient under the fixed math (seeded RNG, session rolled back). The generator is stochastic (one-pot roll, non-veg slot shuffle, pool ordering), so dish diffs are **indicative, not deterministic** — the target deltas are exact, the dish lists show the direction and scale of churn.

Active pre-fix plans: **52** across **52** patients.

| Patient | TDEE | Meal | Old target | New target | Delta |
|---|---|---|---|---|---|
| 1 (Test Patient 001) | 2093 | Breakfast | 445 | 523 | +78 |
|  | 2093 | Lunch | 623 | 733 | +110 |
|  | 2093 | Dinner | 445 | 523 | +78 |
|  |  | Buffer | 581 | 314 | -267 |
| 2 (Test Patient 002) | 2348 | Breakfast | 499 | 587 | +88 |
|  | 2348 | Lunch | 698 | 822 | +123 |
|  | 2348 | Dinner | 499 | 587 | +88 |
|  |  | Buffer | 652 | 352 | -299 |
| 3 (Test Patient 003) | 2254 | Breakfast | 479 | 563 | +85 |
|  | 2254 | Lunch | 670 | 789 | +118 |
|  | 2254 | Dinner | 479 | 563 | +85 |
|  |  | Buffer | 625 | 338 | -287 |
| 4 (Test Patient 004) | 1986 | Breakfast | 422 | 496 | +74 |
|  | 1986 | Lunch | 591 | 695 | +104 |
|  | 1986 | Dinner | 422 | 496 | +74 |
|  |  | Buffer | 551 | 298 | -253 |
| 5 (Test Patient 005) | 2445 | Breakfast | 520 | 611 | +92 |
|  | 2445 | Lunch | 727 | 856 | +128 |
|  | 2445 | Dinner | 520 | 611 | +92 |
|  |  | Buffer | 679 | 367 | -312 |
| 6 (Test Patient 006) | 2123 | Breakfast | 451 | 531 | +80 |
|  | 2123 | Lunch | 631 | 743 | +111 |
|  | 2123 | Dinner | 451 | 531 | +80 |
|  |  | Buffer | 589 | 318 | -271 |
| 7 (Test Patient 007) | 1541 | Breakfast | 327 | 385 | +58 |
|  | 1541 | Lunch | 458 | 539 | +81 |
|  | 1541 | Dinner | 327 | 385 | +58 |
|  |  | Buffer | 428 | 231 | -196 |
| 8 (Test Patient 008) | 2594 | Breakfast | 551 | 649 | +97 |
|  | 2594 | Lunch | 772 | 908 | +136 |
|  | 2594 | Dinner | 551 | 649 | +97 |
|  |  | Buffer | 720 | 389 | -331 |
| 9 (Test Patient 009) | 1831 | Breakfast | 389 | 458 | +69 |
|  | 1831 | Lunch | 545 | 641 | +96 |
|  | 1831 | Dinner | 389 | 458 | +69 |
|  |  | Buffer | 508 | 275 | -233 |
| 10 (Test Patient 010) | 2060 | Breakfast | 438 | 515 | +77 |
|  | 2060 | Lunch | 613 | 721 | +108 |
|  | 2060 | Dinner | 438 | 515 | +77 |
|  |  | Buffer | 572 | 309 | -263 |
| 11 (Test Patient 011) | 2141 | Breakfast | 455 | 535 | +80 |
|  | 2141 | Lunch | 637 | 749 | +112 |
|  | 2141 | Dinner | 455 | 535 | +80 |
|  |  | Buffer | 594 | 321 | -273 |
| 12 (Test Patient 012) | 1913 | Breakfast | 407 | 478 | +72 |
|  | 1913 | Lunch | 569 | 670 | +100 |
|  | 1913 | Dinner | 407 | 478 | +72 |
|  |  | Buffer | 531 | 287 | -244 |
| 13 (Test Patient 013) | 1764 | Breakfast | 375 | 441 | +66 |
|  | 1764 | Lunch | 525 | 618 | +93 |
|  | 1764 | Dinner | 375 | 441 | +66 |
|  |  | Buffer | 490 | 265 | -225 |
| 14 (Test Patient 014) | 2293 | Breakfast | 487 | 573 | +86 |
|  | 2293 | Lunch | 682 | 802 | +120 |
|  | 2293 | Dinner | 487 | 573 | +86 |
|  |  | Buffer | 636 | 344 | -292 |
| 15 (Test Patient 015) | 2167 | Breakfast | 460 | 542 | +81 |
|  | 2167 | Lunch | 645 | 758 | +114 |
|  | 2167 | Dinner | 460 | 542 | +81 |
|  |  | Buffer | 601 | 325 | -276 |
| 16 (Test Patient 016) | 1920 | Breakfast | 408 | 480 | +72 |
|  | 1920 | Lunch | 571 | 672 | +101 |
|  | 1920 | Dinner | 408 | 480 | +72 |
|  |  | Buffer | 533 | 288 | -245 |
| 17 (Test Patient 017) | 1740 | Breakfast | 370 | 435 | +65 |
|  | 1740 | Lunch | 518 | 609 | +91 |
|  | 1740 | Dinner | 370 | 435 | +65 |
|  |  | Buffer | 483 | 261 | -222 |
| 18 (Test Patient 018) | 2223 | Breakfast | 472 | 556 | +83 |
|  | 2223 | Lunch | 661 | 778 | +117 |
|  | 2223 | Dinner | 472 | 556 | +83 |
|  |  | Buffer | 617 | 333 | -283 |
| 19 (Test Patient 019) | 2081 | Breakfast | 442 | 520 | +78 |
|  | 2081 | Lunch | 619 | 728 | +109 |
|  | 2081 | Dinner | 442 | 520 | +78 |
|  |  | Buffer | 578 | 312 | -265 |
| 20 (Test Patient 020) | 1688 | Breakfast | 359 | 422 | +63 |
|  | 1688 | Lunch | 502 | 591 | +89 |
|  | 1688 | Dinner | 359 | 422 | +63 |
|  |  | Buffer | 468 | 253 | -215 |
| 21 (Test Patient 021) | 1953 | Breakfast | 415 | 488 | +73 |
|  | 1953 | Lunch | 581 | 684 | +103 |
|  | 1953 | Dinner | 415 | 488 | +73 |
|  |  | Buffer | 542 | 293 | -249 |
| 22 (Test Patient 022) | 2322 | Breakfast | 493 | 581 | +87 |
|  | 2322 | Lunch | 691 | 813 | +122 |
|  | 2322 | Dinner | 493 | 581 | +87 |
|  |  | Buffer | 644 | 348 | -296 |
| 23 (Test Patient 023) | 2163 | Breakfast | 460 | 541 | +81 |
|  | 2163 | Lunch | 643 | 757 | +114 |
|  | 2163 | Dinner | 460 | 541 | +81 |
|  |  | Buffer | 600 | 324 | -276 |
| 24 (Test Patient 024) | 2054 | Breakfast | 436 | 513 | +77 |
|  | 2054 | Lunch | 611 | 719 | +108 |
|  | 2054 | Dinner | 436 | 513 | +77 |
|  |  | Buffer | 570 | 308 | -262 |
| 25 (Test Patient 025) | 1951 | Breakfast | 415 | 488 | +73 |
|  | 1951 | Lunch | 580 | 683 | +102 |
|  | 1951 | Dinner | 415 | 488 | +73 |
|  |  | Buffer | 541 | 293 | -249 |
| 26 (Test Patient 026) | 2022 | Breakfast | 430 | 506 | +76 |
|  | 2022 | Lunch | 602 | 708 | +106 |
|  | 2022 | Dinner | 430 | 506 | +76 |
|  |  | Buffer | 561 | 303 | -258 |
| 27 (Test Patient 027) | 2193 | Breakfast | 466 | 548 | +82 |
|  | 2193 | Lunch | 652 | 768 | +115 |
|  | 2193 | Dinner | 466 | 548 | +82 |
|  |  | Buffer | 609 | 329 | -280 |
| 28 (Test Patient 028) | 1953 | Breakfast | 415 | 488 | +73 |
|  | 1953 | Lunch | 581 | 684 | +103 |
|  | 1953 | Dinner | 415 | 488 | +73 |
|  |  | Buffer | 542 | 293 | -249 |
| 29 (Test Patient 029) | 2664 | Breakfast | 566 | 666 | +100 |
|  | 2664 | Lunch | 793 | 932 | +140 |
|  | 2664 | Dinner | 566 | 666 | +100 |
|  |  | Buffer | 739 | 400 | -340 |
| 30 (Test Patient 030) | 2147 | Breakfast | 456 | 537 | +81 |
|  | 2147 | Lunch | 639 | 751 | +113 |
|  | 2147 | Dinner | 456 | 537 | +81 |
|  |  | Buffer | 596 | 322 | -274 |
| 31 (Test Patient 031) | 1986 | Breakfast | 422 | 497 | +74 |
|  | 1986 | Lunch | 591 | 695 | +104 |
|  | 1986 | Dinner | 422 | 497 | +74 |
|  |  | Buffer | 551 | 298 | -253 |
| 32 (Test Patient 032) | 1850 | Breakfast | 393 | 462 | +69 |
|  | 1850 | Lunch | 550 | 647 | +97 |
|  | 1850 | Dinner | 393 | 462 | +69 |
|  |  | Buffer | 513 | 277 | -236 |
| 33 (Test Patient 033) | 1583 | Breakfast | 336 | 396 | +59 |
|  | 1583 | Lunch | 471 | 554 | +83 |
|  | 1583 | Dinner | 336 | 396 | +59 |
|  |  | Buffer | 439 | 237 | -202 |
| 34 (Test Patient 034) | 2496 | Breakfast | 530 | 624 | +94 |
|  | 2496 | Lunch | 742 | 873 | +131 |
|  | 2496 | Dinner | 530 | 624 | +94 |
|  |  | Buffer | 693 | 374 | -318 |
| 35 (Test Patient 035) | 1965 | Breakfast | 418 | 491 | +74 |
|  | 1965 | Lunch | 585 | 688 | +103 |
|  | 1965 | Dinner | 418 | 491 | +74 |
|  |  | Buffer | 545 | 295 | -251 |
| 36 (Test Patient 036) | 1891 | Breakfast | 402 | 473 | +71 |
|  | 1891 | Lunch | 563 | 662 | +99 |
|  | 1891 | Dinner | 402 | 473 | +71 |
|  |  | Buffer | 525 | 284 | -241 |
| 37 (Test Patient 037) | 2086 | Breakfast | 443 | 522 | +78 |
|  | 2086 | Lunch | 621 | 730 | +110 |
|  | 2086 | Dinner | 443 | 522 | +78 |
|  |  | Buffer | 579 | 313 | -266 |
| 38 (Test Patient 038) | 2079 | Breakfast | 442 | 520 | +78 |
|  | 2079 | Lunch | 619 | 728 | +109 |
|  | 2079 | Dinner | 442 | 520 | +78 |
|  |  | Buffer | 577 | 312 | -265 |
| 39 (Test Patient 039) | 1893 | Breakfast | 402 | 473 | +71 |
|  | 1893 | Lunch | 563 | 663 | +99 |
|  | 1893 | Dinner | 402 | 473 | +71 |
|  |  | Buffer | 525 | 284 | -241 |
| 40 (Test Patient 040) | 1717 | Breakfast | 365 | 429 | +64 |
|  | 1717 | Lunch | 511 | 601 | +90 |
|  | 1717 | Dinner | 365 | 429 | +64 |
|  |  | Buffer | 477 | 258 | -219 |
| 41 (Test Patient 041) | 1437 | Breakfast | 305 | 359 | +54 |
|  | 1437 | Lunch | 428 | 503 | +75 |
|  | 1437 | Dinner | 305 | 359 | +54 |
|  |  | Buffer | 399 | 216 | -183 |
| 42 (Test Patient 042) | 1979 | Breakfast | 420 | 495 | +74 |
|  | 1979 | Lunch | 589 | 693 | +104 |
|  | 1979 | Dinner | 420 | 495 | +74 |
|  |  | Buffer | 549 | 297 | -252 |
| 43 (Test Patient 043) | 1730 | Breakfast | 368 | 432 | +65 |
|  | 1730 | Lunch | 515 | 605 | +91 |
|  | 1730 | Dinner | 368 | 432 | +65 |
|  |  | Buffer | 480 | 259 | -221 |
| 44 (Test Patient 044) | 2028 | Breakfast | 431 | 507 | +76 |
|  | 2028 | Lunch | 603 | 710 | +106 |
|  | 2028 | Dinner | 431 | 507 | +76 |
|  |  | Buffer | 563 | 304 | -259 |
| 45 (Test Patient 045) | 1502 | Breakfast | 319 | 375 | +56 |
|  | 1502 | Lunch | 447 | 526 | +79 |
|  | 1502 | Dinner | 319 | 375 | +56 |
|  |  | Buffer | 417 | 225 | -191 |
| 46 (Test Patient 046) | 3032 | Breakfast | 644 | 758 | +114 |
|  | 3032 | Lunch | 902 | 1061 | +159 |
|  | 3032 | Dinner | 644 | 758 | +114 |
|  |  | Buffer | 841 | 455 | -387 |
| 47 (Test Patient 047) | 2855 | Breakfast | 607 | 714 | +107 |
|  | 2855 | Lunch | 849 | 999 | +150 |
|  | 2855 | Dinner | 607 | 714 | +107 |
|  |  | Buffer | 792 | 428 | -364 |
| 48 (Test Patient 048) | 2930 | Breakfast | 623 | 733 | +110 |
|  | 2930 | Lunch | 872 | 1026 | +154 |
|  | 2930 | Dinner | 623 | 733 | +110 |
|  |  | Buffer | 813 | 440 | -374 |
| 49 (Test Patient 049) | 1878 | Breakfast | 399 | 470 | +70 |
|  | 1878 | Lunch | 559 | 657 | +99 |
|  | 1878 | Dinner | 399 | 470 | +70 |
|  |  | Buffer | 521 | 282 | -239 |
| 50 (Test Patient 050) | 1833 | Breakfast | 389 | 458 | +69 |
|  | 1833 | Lunch | 545 | 641 | +96 |
|  | 1833 | Dinner | 389 | 458 | +69 |
|  |  | Buffer | 509 | 275 | -234 |
| 51 (Test Patient) | 1761 | Breakfast | 374 | 440 | +66 |
|  | 1761 | Lunch | 524 | 616 | +92 |
|  | 1761 | Dinner | 374 | 440 | +66 |
|  |  | Buffer | 489 | 264 | -225 |
| 53 (Priya Test) | 1867 | Breakfast | 397 | 467 | +70 |
|  | 1867 | Lunch | 555 | 653 | +98 |
|  | 1867 | Dinner | 397 | 467 | +70 |
|  |  | Buffer | 518 | 280 | -238 |

## Per-patient dish diff (indicative — see caveat above)

### Patient 1 — Test Patient 001
Stored plan: 38 distinct dishes; regenerated: 36; kept: 10.
- Would drop: Aloo Baingan, Chole Pindi, Classic Indian Sliced Salad, Cranberry Naan, Curd Oats, Dahi Methi Puri, Green Beans Fry, Green Chilli Sabzi, Greens Rava Puliyodharai, Kandarappam, Lacha Onion, Maida Luchi, Masoor Dal And Rajma Masala, Methi Pakoda Kadhi, Moong Dal, Moong Dal Pani, Multani Kaali Arbi, Navrang Dal, Paneer Makhani, Phulka, Pudina Pyaz Kachumber Salad, Ragi Sankati, Rajasthani Ghasela, Rajasthani Methi Mangodi Sabzi, Shimla Mirch Ki Launji, Steamed Chawal, Steamed Rice, Sweet Potato And Bitter Gourd Kulambu
- Would add: Besan Capsicum Ki Sabzi, Cucumber Raita, Curd Rice With Carrots, Dahi Bowl, Dal Chawal, Dal Kabila, Dal Khichdi, Dubki Wale Aloo, Hara Pyaz Paratha, Khichdi Roti ??????, Masala Chaas, Masala Roasted Aloo, Matar Poha, Meethi Lassi, Millet Khichdi, Mixed Millet Khichdi, Moong Dal Khichdi, Oats Banana Apple Porridge, Plain Dahi, Plain Dahi Raita, Potato Onion Cheela, Ragi Oatmeal Kanji, Rajma Chawal, Savoury Oatmeal Porridge, Soya Methi Palak Ki Sabzi, Vegetable Sambar

### Patient 2 — Test Patient 002
Stored plan: 29 distinct dishes; regenerated: 40; kept: 18.
- Would drop: Carrots Dill And Peanut Sadam, Dahi Methi Puri, Dal Chawal, Egg Pulao, Gongura Pulihora, Lachedar Kakdi Pyaz Kachumber, Lentil Bread Buttermilk, Milagu Sadam, Moong Dal Khichdi, Prawn Drumstick Curry, Thengai Saadam
- Would add: Akki Roti, Aloo Bharta, Aloo Coconut Sabzi, Avarekalu Usli, Beans Fry, Carrot And Capsicum Rice, Cauliflower And Red Bell Pepper Stir Fry, Chicken Changezi, Curd Oats, Green Beans Fry, Hara Pyaz Paratha, Jolada Roti, Konaseema Kodi Kura, Moong Dal Methi Ki Sabzi, Oats Banana Apple Porridge, Obbattu Saaru, Phulka, Ragi Sankati, Sabbasige Rasam, Sorakkai Palya, Steamed White Rice, Togarikaayi Usli

### Patient 3 — Test Patient 003
Stored plan: 46 distinct dishes; regenerated: 37; kept: 26.
- Would drop: Banana Apple Mash, Bengali Luchi, Creamy Beetroot And Potato Puree, Curry Fried Quinoa Rice, Dahi Methi Puri, Dal Pitha, Dill Cucumber Raita, Hyderabadi Khatti Dal, Lachedar Kakdi Pyaz Kachumber, Maida Luchi, Masala Roasted Aloo, Mixed Vegetable Fry, Moong Dal Pani, Palak And Kala Chana Sukhi Sabzi, Pudina Pyaz Kachumber Salad, Pumpkin Chokka, Ragi Oatmeal Kanji, Steamed Chawal, Sweet Potato And Bitter Gourd Kulambu, Whole Wheat Roti
- Would add: Beans Fry, Carrot And Capsicum Rice, Cucumber Pineapple Raw Mango Salad, Green Beans Fry, Matar Paneer Pulao, Matta Rice Peas Pulao, Moong Dal Methi Ki Sabzi, Onion Raita, Potato Onion Cheela, Shak Bhaja, Spicy Cabbage Rice

### Patient 4 — Test Patient 004
Stored plan: 44 distinct dishes; regenerated: 43; kept: 31.
- Would drop: Banana Apple Mash, Beans Fry, Besan Chila Stuffed With Chatap Paneer, Classic Indian Sliced Salad, Curry Fried Quinoa Rice, Dhokla, Dill Cucumber Raita, Gatte Ki Sabzi, Green Beans Fry, Hyderabadi Khatti Dal, Moong Dal Pani, Plain Poha, Tindora Sambharo
- Would add: Banana Filos, Creamy Beetroot And Potato Puree, Goan Chana Ros, Khichdi Roti ??????, Masala Roasted Aloo, Moong Dal Khichdi, Palak And Kala Chana Sukhi Sabzi, Savoury Oatmeal Porridge, Sindhi Kadhi, Spicy Mushrooms, Vegetable Sambar, Warm Red Lentil Salad With Goat Cheese

### Patient 5 — Test Patient 005
Stored plan: 45 distinct dishes; regenerated: 38; kept: 19.
- Would drop: Banana Ragi Porridge, Besan Capsicum Ki Sabzi, Buttered Peas Puree, Chickpea Potato, Country Chicken, Dal Chawal, Dal Kabila, Gawar Pods Fenugreek Vegetable, Hara Dhania Paratha, Kakdi Koshimbir, Lachedar Kakdi Pyaz Kachumber, Masala Roasted Aloo, Masoor Dal And Rajma Masala, Moong Dal Khichdi, Multani Kaali Arbi, Multigrain Roti, Murg Anardana, Oats Banana Apple Porridge, Onion Raita, Pahari Aloo Palda, Paneer Makhani, Phulka, Prawn Drumstick Curry, Rajgira Paneer Paratha, Salan, Soya Methi Palak Ki Sabzi
- Would add: Aloo Bharta, Aloo Matar Paneer, Beans Fry, Carrot And Capsicum Rice, Chana Methi Dal, Chicken Biryani, Chicken Changezi, Chicken Handi, Dahi Bowl, Dal Khichdi, Green Beans Fry, Kachumber Salad, Masoor Dal, Mixed Millet Khichdi, No Onion No Garlic Aloo Gajar Ki Sabzi, Paneer Butter Masala, Plain Wheat Paratha, Spiced Khooba Roti, Spicy Cabbage Rice

### Patient 6 — Test Patient 006
Stored plan: 35 distinct dishes; regenerated: 49; kept: 30.
- Would drop: Carrots Dill And Peanut Sadam, Curd Rice With Carrots, Curry Fried Quinoa Rice, Gongura Pulihora, No Onion No Garlic Sambar Rice
- Would add: Akki Roti, Aloo Methi, Chana Methi Dal, Crispy Vegetable, Dal Bharta, Dal Gravy, Greens Rava Puliyodharai, Hara Pyaz Paratha, Jolada Roti, Kachumber Salad, Kandarappam, Karatya Kismore, Lentil Bread Buttermilk, Milagu Sadam, Multani Kaali Arbi, Pacha Payir Kulambu, Sabsige Soppu Kootu, Stuffed Karela With Aloo, Ulva Charu

### Patient 7 — Test Patient 007
Stored plan: 45 distinct dishes; regenerated: 45; kept: 35.
- Would drop: Bhindi Masala, Chole Masala, Curry Fried Quinoa Rice, Gavarfali Ki Sukhi Sabzi, Gawarfli Dry Vegetable, Kandarappam, Raw Mango Raita, Sada Dahi, Sukhe Chole, Vegetable Jowar Upma
- Would add: Avarakkai Kootu, Chana Methi Dal, Chickpea Potato, Dali Thoy, Egg Scramble With Drumstick Leaves, Mixed Vegetable Filling, Moong Dal Methi Ki Sabzi, Stuffed Karela With Aloo, Watermelon Seeds Rice, Whole Wheat Chapati

### Patient 8 — Test Patient 008
Stored plan: 35 distinct dishes; regenerated: 47; kept: 26.
- Would drop: Avakai Chicken Biryani, Bihari Kale Gram Roti, Chicken Pulao, Curd Rice With Carrots, Dal Chawal, Kachumber Salad, Millet Khichdi, Moong Dal Khichdi, Savoury Oatmeal Porridge
- Would add: Aloo Bharta, Avarakkai Kootu, Avarekalu Usli, Bhugi Dal Paratha, Cabbage Bhurji, Chicken Biryani, Dahi Bowl, Fish Curry, Greens Rava Puliyodharai, Hara Pyaz Paratha, Hyderabadi Khatti Dal, Kala Chana Masala Curry, Karatya Kismore, Kothavarangai Poriyal, Maida Luchi, Mixed Vegetable Filling, Multigrain Roti, Plain Dahi Raita, Pudina Moong Dal, Sattu Litti, Tawa Paratha

### Patient 9 — Test Patient 009
Stored plan: 43 distinct dishes; regenerated: 49; kept: 35.
- Would drop: Banana Apple Mash, Classic Indian Sliced Salad, Curd Rice With Carrots, Curry Fried Quinoa Rice, Foxtail Millet Paruppu Adai With Keerai, Mixed Vegetable Filling, Vegetable Jowar Upma, Watermelon Seeds Rice
- Would add: Avarakkai Kootu, Chana Methi Dal, Dahi Methi Puri, Greens Rava Puliyodharai, Hara Pyaz Paratha, Hyderabadi Khatti Dal, Karatya Kismore, Kothavarangai Poriyal, Makki Dhokla, Mung Bean Sprouts Upkari, Paneer Masala Dosa -Paneer Bhurji Dosa, Steamed Chawal, Sweet Potato And Bitter Gourd Kulambu, Vegetable Sambar

### Patient 10 — Test Patient 010
Stored plan: 34 distinct dishes; regenerated: 35; kept: 29.
- Would drop: Carrots Dill And Peanut Sadam, Curd Rice With Carrots, Curry Fried Quinoa Rice, Kachumber Salad, Medu Vada
- Would add: Dal Gravy, Gongura Pulihora, Gorai Kai Kara, Kothavarangai Poriyal, Lentil Bread Buttermilk, Milagu Sadam

### Patient 11 — Test Patient 011
Stored plan: 32 distinct dishes; regenerated: 43; kept: 22.
- Would drop: Aloo Parwal, Dahi Methi Puri, Ellu Sadam, Green Chilli Sabzi, Hyderabadi Khatti Dal, Matar Millet Pulao, Matta Rice Peas Pulao, Moong Dal Pani, Quinoa Brown Rice And Vegetable Pulao, Tandoori Paneer
- Would add: Banana Ragi Porridge, Butter Chicken With Tandoori Mayo, Buttered Peas Puree, Chickpea Potato, Curd Oats, Dal Kabila, Hara Dhania Paratha, Hara Pyaz Paratha, Kachumber Salad, Makki Dhokla, Masoor Dal And Rajma Masala, Masoor Dal Makhani, Methi Malai Matar, Multani Kaali Arbi, Oats Banana Apple Porridge, Palak And Kala Chana Sukhi Sabzi, Paneer Makhani, Potato Onion Cheela, Soya Methi Palak Ki Sabzi, Warm Red Lentil Salad With Goat Cheese, Whole Wheat Chapati

### Patient 12 — Test Patient 012
Stored plan: 34 distinct dishes; regenerated: 41; kept: 23.
- Would drop: Avarekalu Usli, Beans Fry, Cauliflower And Red Bell Pepper Stir Fry, Gojju Avalakki, Green Beans Fry, Kachumber Salad, Pappu Charu, Quinoa Vangi Bath, Ragi Kanji, Rasam, Sabbasige Rasam
- Would add: Bangaladumpa Vepudu, Beans Cauliflower Poriyal, Bell Saaru, Egg Lifafa Paratha, Green Moong Dal Kootu, Hara Pyaz Paratha, Hyderabadi Khatti Dal, Lentil Bread Buttermilk, Makki Dhokla, Matta Rice Peas Pulao, Miriyala Charu, Oats Banana Apple Porridge, Ridge Gourd Sabzi, Sabsige Soppu Kootu, Sweet Potato And Bitter Gourd Kulambu, Vazhaipoo Paruppu Usili, Vegetable Sambar, Vendakkai-Vazhakkai Mor Kuzhambu

### Patient 13 — Test Patient 013
Stored plan: 38 distinct dishes; regenerated: 39; kept: 30.
- Would drop: Baingan Chokha, Banana Ragi Porridge, Besan Chila Stuffed With Chatap Paneer, Buttered Peas Puree, Classic Indian Sliced Salad, Hara Dhania Paratha, Oats Banana Apple Porridge, Raw Mango Raita
- Would add: Beans Fry, Curd Oats, Green Beans Fry, Maida Luchi, Makki Dhokla, Pudina Pyaz Kachumber Salad, Ragi Oatmeal Kanji, Vegetable Sambar, Whole Wheat Roti

### Patient 14 — Test Patient 014
Stored plan: 39 distinct dishes; regenerated: 37; kept: 26.
- Would drop: Banana Ragi Porridge, Dahi Methi Puri, Hara Pyaz Paratha, Jadoh, Masala Roasted Aloo, Methi Malai Matar, Oats Banana Apple Porridge, Palak And Kala Chana Sukhi Sabzi, Plain Dahi, Plain Dahi Raita, Sindhi Kadhi, Tindora Sambharo, Warm Red Lentil Salad With Goat Cheese
- Would add: Chicken Changezi, Cucumber Pineapple Raw Mango Salad, Doodh Dudhi, Egg Bhurji, Jhinga Gavar, Matta Rice Peas Pulao, Multigrain Roti, Murg Anardana, Rava Fried Prawns, Sheganchi Amti, Vegetable Sambar

### Patient 15 — Test Patient 015
Stored plan: 39 distinct dishes; regenerated: 42; kept: 28.
- Would drop: Aloo Parwal, Dahi Methi Puri, Ellu Sadam, Green Chilli Sabzi, Hyderabadi Khatti Dal, Methi Pakoda Kadhi, Moong Dal Pani, Pahari Aloo Palda, Rajasthani Methi Mangodi Sabzi, Sweet Potato And Bitter Gourd Kulambu, Tandoori Paneer
- Would add: Banana Ragi Porridge, Chickpea Potato, Dal Kabila, Hara Pyaz Paratha, Kachumber Salad, Masoor Dal And Rajma Masala, Masoor Dal Makhani, Multani Kaali Arbi, Onion Raita, Palak And Kala Chana Sukhi Sabzi, Paneer Makhani, Potato Onion Cheela, Soya Methi Palak Ki Sabzi, Warm Red Lentil Salad With Goat Cheese

### Patient 16 — Test Patient 016
Stored plan: 36 distinct dishes; regenerated: 42; kept: 25.
- Would drop: Bisi Bele Bath, Curry Fried Quinoa Rice, Gojju Avalakki, Kachumber Salad, No Onion No Garlic Sambar Rice, Quick And Easy Bread Upma, Rasam, Semiya Upma, Spinach Idli, Togarikalu Akki, Watermelon Seeds Rice
- Would add: Bele Dose, Carrots Dill And Peanut Sadam, Chana Methi Dal, Dahi Methi Puri, Green Moong Dal Kootu, Hara Dhania Paratha, Jeera Rice, Jolada Roti, Makki Dhokla, Moong Dal Khichdi, Paneer Masala Dosa -Paneer Bhurji Dosa, Potato Sagu For Rava Idli, Ragi Oatmeal Kanji, Ragi Sankati, Spring Onion Dosa, Thengai Saadam, Valval

### Patient 17 — Test Patient 017
Stored plan: 42 distinct dishes; regenerated: 43; kept: 29.
- Would drop: Beetroot Loni Sponge Dosa, Besan Capsicum Ki Sabzi, Besan Chila Stuffed With Chatap Paneer, Bhindi Masala, Chickpea Potato, Dal Tadka, Hare Chane Ka Pulav, Kandarappam, Lachedar Kakdi Pyaz Kachumber, Quick And Easy Bread Upma, Ragi Dosa, Raw Banana & Ajwain Paratha, Watermelon Seeds Rice
- Would add: Beans Fry, Cranberry Naan, Dahi Methi Puri, Dill Cucumber Raita, Egg Lifafa Paratha, Egg Scramble With Drumstick Leaves, Kara Boondi Kurma, Makki Dhokla, Masoor Dal, Matar Poha, Mixed Millet Khichdi, Moong Dal Khichdi, Navrang Dal, Spiced Khooba Roti

### Patient 18 — Test Patient 018
Stored plan: 44 distinct dishes; regenerated: 45; kept: 36.
- Would drop: Banana Ragi Porridge, Creamy Beetroot And Potato Puree, Curd Rice With Carrots, Curry Fried Quinoa Rice, Dahi Methi Puri, Hyderabadi Khatti Dal, Quick And Easy Bread Upma, Sweet Potato And Bitter Gourd Kulambu
- Would add: Adraki Rajma Masala, Beans Fry, Carrot And Capsicum Rice, Greens Rava Puliyodharai, Onion Raita, Paneer Butter Masala, Potato Onion Cheela, Ragi Adai, Tadka Dal

### Patient 19 — Test Patient 019
Stored plan: 50 distinct dishes; regenerated: 43; kept: 33.
- Would drop: Aloo Bharta, Bengali Luchi, Bhakri, Chicken Changezi, Dahi Bowl, Dahi Methi Puri, Egg Curry, Gatte Ki Sabzi, Green Beans Fry, Gujarati Kadhi, Hyderabadi Khatti Dal, Kachumber Salad, Kandarappam, Moong Dal Pani, Phulka, Pudina Pyaz Kachumber Salad, Tindora Sambharo
- Would add: Besan Pithla, Chana Masala, Chicken Pulao, Dal Chawal, Egg Bhurji, Moong Dal Khichdi, Murg Anardana, Rava Fried Prawns, Ridge Gourd Sabzi, Savoury Oatmeal Porridge

### Patient 20 — Test Patient 020
Stored plan: 45 distinct dishes; regenerated: 42; kept: 30.
- Would drop: Banana Apple Mash, Bisi Bele Bath, Carrots Dill And Peanut Sadam, Fermented Rice Appam, Kandi Pachadi, Lachedar Kakdi Pyaz Kachumber, Lemon Rice, Malabar Curry, Masala Dosa, Peerkangai Thogayal, Raw Mango Raita, Steamed Rice Idli, Steamed Rice Puttu, Sweet Corn Upma, Ven Pongal
- Would add: Cauliflower And Red Bell Pepper Stir Fry, Curd Rice With Carrots, Curry Fried Quinoa Rice, Dill Cucumber Raita, Kara Boondi Kurma, Menthe Kadubu, No Onion No Garlic Sambar Rice, Quick And Easy Bread Upma, Sambar, Spinach Idli, Steamed White Rice, Togarikalu Akki

### Patient 21 — Test Patient 021
Stored plan: 38 distinct dishes; regenerated: 36; kept: 29.
- Would drop: Banana Ragi Porridge, Classic Indian Sliced Salad, Curd Rice With Carrots, Curry Fried Quinoa Rice, Dill Cucumber Raita, Hara Dhania Paratha, Kachumber Salad, Kakdi Koshimbir, Raw Banana & Ajwain Paratha
- Would add: Curd Oats, Millet Khichdi, Mung Bean Sprouts Upkari, Rajma Chawal, Vegetable Sambar, Verkadalai Sundal- Peanut Sundal, Whole Wheat Chapati

### Patient 22 — Test Patient 022
Stored plan: 34 distinct dishes; regenerated: 39; kept: 26.
- Would drop: Avakai Chicken Biryani, Dal Gravy, Gongura Pulihora, Kakdi Koshimbir, Kandarappam, Moong Dal Khichdi, Prawn Drumstick Curry, Thengai Saadam
- Would add: Aloo Bharta, Amla Gawar, Carrot And Capsicum Rice, Chicken Changezi, Curd Oats, Dal Bharta, Hara Pyaz Paratha, Jolada Roti, Kala Chana Masala Curry, Konaseema Kodi Kura, Masoor Moong Phali Ki Dal, Phulka, Verkadalai Sundal- Peanut Sundal

### Patient 23 — Test Patient 023
Stored plan: 40 distinct dishes; regenerated: 46; kept: 35.
- Would drop: Creamy Beetroot And Potato Puree, Curd Rice With Carrots, Maharashtrian Masale Baath, Moong Dal Khichdi, Pudina Pyaz Kachumber Salad
- Would add: Amla Gawar, Buttered Peas Puree, Green Moong Dal Curry, Hara Pyaz Paratha, Kakdi Koshimbir, Maida Luchi, Onion Raita, Paneer Butter Masala, Sattu Litti, Tadka Dal, Verkadalai Sundal- Peanut Sundal

### Patient 24 — Test Patient 024
Stored plan: 45 distinct dishes; regenerated: 41; kept: 38.
- Would drop: Andhra Steel Kandi Attu, Banana Ragi Porridge, Cucumber Raita, Dill Cucumber Raita, Kachumber Salad, Pudina Pyaz Kachumber Salad, Tindora Sambharo
- Would add: Amla Gawar, Moong Dal Khichdi, Ridge Gourd Sabzi

### Patient 25 — Test Patient 025
Stored plan: 38 distinct dishes; regenerated: 44; kept: 30.
- Would drop: Classic Indian Sliced Salad, Curd Rice With Carrots, Curry Fried Quinoa Rice, Dill Cucumber Raita, Kachumber Salad, Mixed Millet Khichdi, Moong Dal Khichdi, Raw Banana & Ajwain Paratha
- Would add: Aloo Methi, Avarekalu Usli, Creamy Beetroot And Potato Puree, Dahi Methi Puri, Dal Bharta, Green Moong Dal Curry, Hara Pyaz Paratha, Mung Bean Sprouts Upkari, Oats Banana Apple Porridge, Parwal Masala, Spiced Khooba Roti, Vegetable Sambar, Verkadalai Sundal- Peanut Sundal, Whole Wheat Chapati

### Patient 26 — Test Patient 026
Stored plan: 41 distinct dishes; regenerated: 44; kept: 20.
- Would drop: Banana Apple Mash, Bhakri, Cauliflower And Red Bell Pepper Stir Fry, Chow Chow Curry, Classic Indian Sliced Salad, Curd Rice With Carrots, Dahi Methi Puri, Dill Cucumber Raita, Drumstick Greens Sambar, Fish Curry, Hara Dhania Paratha, Kachumber Salad, Kakdi Koshimbir, Malabar Curry, Multigrain Roti, No Onion No Garlic Sambar Rice, Phulka, Poosanikai Sambar, Pudina Pyaz Kachumber Salad, Rasam, Tamarind Gojju
- Would add: Andhra Vankaya Fry With Peanuts, Appam, Avakai Chicken Biryani, Bendekayi Gojju, Dahi Bowl, Drumstick Spinach Fry With Moong Dal, Gongura Pulihora, Hara Pyaz Paratha, Jolada Roti, Konaseema Kodi Kura, Kovakkai Podi Curry, Lachedar Kakdi Pyaz Kachumber, Miriyala Charu, Mixed Vegetable Koora, Mulakootal, Peerkangai Thogayal, Ridge Gourd Sabzi, Sabsige Soppu Kootu, Sada Chawal, Senai Potato Fry, Steamed Rice, Thengai Saadam, Thotakura Pappu, Yellow Cucumber Dal

### Patient 27 — Test Patient 027
Stored plan: 40 distinct dishes; regenerated: 46; kept: 19.
- Would drop: Aloo Baingan, Aloo Methi, Aloo Parwal, Curd Rice With Carrots, Curry Fried Quinoa Rice, Dahi Methi Puri, Green Chilli Sabzi, Hyderabadi Khatti Dal, Kala Chana Masala Curry, Lacha Onion, Millet Khichdi, Mixed Millet Khichdi, Moong Dal Pani, Pahari Aloo Palda, Quick And Easy Bread Upma, Rajasthani Dal, Rajasthani Ghasela, Rajasthani Methi Mangodi Sabzi, Raw Banana & Ajwain Paratha, Sweet Potato And Bitter Gourd Kulambu, Tandoori Paneer
- Would add: Beans Fry, Besan Capsicum Ki Sabzi, Buttered Peas Puree, Chatpatti Makai Masala, Dahi Wale Paneer, Dal Gravy, Dal Khichdi, Green Beans Fry, Greens Rava Puliyodharai, Kachumber Salad, Kakdi Koshimbir, Khichdi Roti ??????, Masoor Dal Makhani, Masoor Moong Phali Ki Dal, Moong Dal Methi Ki Sabzi, Multani Kaali Arbi, Onion Raita, Palak And Kala Chana Sukhi Sabzi, Paneer Kulcha, Paneer Makhani, Paneer Shashlik, Patta Gobi Matar Nu Shaak, Phulka, Potato Onion Cheela, Savoury Oatmeal Porridge, Soya Methi Palak Ki Sabzi, Warm Red Lentil Salad With Goat Cheese

### Patient 28 — Test Patient 028
Stored plan: 47 distinct dishes; regenerated: 47; kept: 35.
- Would drop: Baingan Chokha, Banana Ragi Porridge, Beans Fry, Classic Indian Sliced Salad, Curry Fried Quinoa Rice, Dill Cucumber Raita, Doi Chira, Green Beans Fry, Hara Dhania Paratha, Moong Dal With Vegetables, Onion Raita, Quick And Easy Bread Upma
- Would add: Buttered Peas Puree, Carrot And Capsicum Rice, Egg Lifafa Paratha, Hara Pyaz Paratha, Khichdi Roti ??????, Masala Roasted Aloo, Mixed Vegetable Fry, Palak And Kala Chana Sukhi Sabzi, Pumpkin Chokka, Ridge Gourd Sabzi, Savoury Oatmeal Porridge, Vegetable Sambar

### Patient 29 — Test Patient 029
Stored plan: 39 distinct dishes; regenerated: 45; kept: 24.
- Would drop: Amlechi Uddamethi, Chana Masala, Chatpatti Makai Masala, Cucumber Pineapple Raw Mango Salad, Dal Chawal, Doodh Dudhi, Green Beans Fry, Jadoh, Lilva Khichdi, Moong Dal Methi Ki Sabzi, Multigrain Roti, Savoury Oatmeal Porridge, Sheganchi Amti, Varan Bhat, Vatana Tonak
- Would add: Bajra Roti, Bardoli Ki Khichdi, Cabbage Bhurji, Chicken Biryani, Corn And Peas Curry, Dal Baati, Egg Dosa With Cheesy Garlic Mayo, Hyderabadi Shahi Mixed Vegetable Curry, Kachcha Kela Masala Sabzi, Kachumber Salad, Matta Rice Peas Pulao, Methi Turai, Oats Banana Apple Porridge, Onion Raita, Plain Dahi Raita, Sindhi Dharan Ji Kadhi, Spicy Cabbage Rice, Spicy Coconut Brinjal, Spicy Mushrooms, Sweet Potato And Bitter Gourd Kulambu, Tawa Paratha

### Patient 30 — Test Patient 030
Stored plan: 48 distinct dishes; regenerated: 39; kept: 18.
- Would drop: Akki Roti, Banana Ragi Porridge, Bangaladumpa Vepudu, Beans Cauliflower Poriyal, Bell Saaru, Brinjal Poriyal Masala, Carrot Beans Poriyal, Carrots Dill And Peanut Sadam, Chow Chow Curry, Creamy Beetroot And Potato Puree, Curd Rice With Carrots, Dahi Methi Puri, Dill Cucumber Raita, Hara Dhania Paratha, Hyderabadi Khatti Dal, Jowar And Vegetable Porridge, Kachumber Salad, Kakdi Koshimbir, Kandarappam, Menthe Kadubu, Moong Dal Khichdi, Moong Dal Pani, Moong Dal Rasam / Retired Pappu Charu, Pudina Pyaz Kachumber Salad, Quick And Easy Bread Upma, Ragi Oatmeal Kanji, Rasam, Sorakkai Kozhukattai Paal Kuzhambu, Tamarind Gojju, Thengai Saadam
- Would add: Beans Usili, Beetroot Garlic Lemon Rasam, Buttered Peas Puree, Dal Chawal, Dondakkai Puli, Gongura Pulihora, Greens Rava Puliyodharai, Khichdi Roti ??????, Menthya Dose, Milagai Podi Uthappam, Milagu Sadam, No Onion No Garlic Sambar Rice, Onion Raita, Palak And Kala Chana Sukhi Sabzi, Palak Pappu, Patoli, Peerkangai Thogayal, Snake Gourd Kootu, Taro Root Curry, Tomato Rasam For Babies And Toddlers, Ulva Charu

### Patient 31 — Test Patient 031
Stored plan: 41 distinct dishes; regenerated: 36; kept: 30.
- Would drop: Beans Fry, Cranberry Naan, Dill Cucumber Raita, Green Beans Fry, Gujarati Kadhi, Kandarappam, Moong Dal Rasam / Retired Pappu Charu, Multani Kaali Arbi, Shimla Mirch Ki Launji, Singhara Ato Chill, Spiced Khooba Roti
- Would add: Creamy Beetroot And Potato Puree, Matar Millet Pulao, Matta Rice Peas Pulao, Parwal Masala, Tandoori Paneer, Vegetable Sambar

### Patient 32 — Test Patient 032
Stored plan: 39 distinct dishes; regenerated: 45; kept: 30.
- Would drop: Beans Fry, Buttered Peas Puree, Green Beans Fry, Lemon Rice, No Onion No Garlic Sambar Rice, Raw Mango Raita, Sabbasige Soppu Dosa, Togarikalu Akki, Watermelon Seeds Rice
- Would add: Beans Cauliflower Poriyal, Brinjal Poriyal Masala, Carrot Beans Poriyal, Chow Chow Curry, Creamy Beetroot And Potato Puree, Gongura Pulihora, Hara Pyaz Paratha, Jaisalmer Kala Chana Kadhi, Jowar And Vegetable Porridge, Moong Dal Khichdi, Ragi Oatmeal Kanji, Sakkaravalli Kizhangu Poriyal, Spring Onion Dosa, Tamarind Gojju, Vegetable Sambar

### Patient 33 — Test Patient 033
Stored plan: 50 distinct dishes; regenerated: 42; kept: 36.
- Would drop: Banana Apple Mash, Basil Tincture, Chickpea Potato, Homemade Idli Dosa Batter, Hyderabadi Khatti Dal, Lentil Bread Buttermilk, Masala Roasted Aloo, Mixed Vegetable Fry, Mochar Ghonto, Plain Bhakri, Rajgira Paneer Paratha, Sada Dahi, Steamed Rice, Sukhe Chole
- Would add: Curd Rice With Carrots, Kara Sevai, Moong Dal Khichdi, Palak Kadhi, Ragi Oatmeal Kanji, Watermelon Seeds Rice

### Patient 34 — Test Patient 034
Stored plan: 40 distinct dishes; regenerated: 37; kept: 25.
- Would drop: Amlechi Uddamethi, Bajra Roti, Buttered Peas Puree, Chatpatti Makai Masala, Creamy Beetroot And Potato Puree, Goan Chana Ros, Goan Chicken Curry, Hyderabadi Khatti Dal, Lentil Bread Buttermilk, Masala Roasted Aloo, Mayo Cheddar Chicken, Plain Dahi, Ragi Kanji, Rajgira Paneer Paratha, Vegetable Raita
- Would add: Cabbage Bhurji, Chingri Paturi, Curd Rice, Goan Moolyacho Ross, Jaisalmer Kala Chana Kadhi, Matta Rice Peas Pulao, No Onion No Garlic Aloo Gajar Ki Sabzi, Pumpkin Raita, Ragi Sankati, Rava Fried Prawns, Senai Pachadi, Vegetable Sambar

### Patient 35 — Test Patient 035
Stored plan: 39 distinct dishes; regenerated: 47; kept: 23.
- Would drop: Aloo Jeera, Banana Apple Mash, Chole Masala, Classic Indian Sliced Salad, Curd Rice With Carrots, Dal Chawal, Dal Tadka, Dill Cucumber Raita, Green Beans Fry, Maharashtrian Masale Baath, Mixed Millet Khichdi, Navrang Dal, Quick And Easy Bread Upma, Raw Banana & Ajwain Paratha, Soya Chaap Curry, Sukhe Chole
- Would add: Aloo Methi, Aloo Parwal, Besan Capsicum Ki Sabzi, Cabbage Soya, Chickpea Potato, Creamy Beetroot And Potato Puree, Hara Pyaz Paratha, Kala Chana Masala Curry, Khichdi Roti ??????, Lachedar Kakdi Pyaz Kachumber, Masala Jowar Methi Roti, Masoor Dal And Rajma Masala, Pahari Aloo Palda, Paneer Kulcha, Paneer Makhani, Parwal Masala, Phulka, Ragi Oatmeal Kanji, Rajasthani Dal, Spiced Khooba Roti, Spinach Paneer Kofta, Sweet Potato And Bitter Gourd Kulambu, Tandoori Paneer, Vegetable Sambar

### Patient 36 — Test Patient 036
Stored plan: 47 distinct dishes; regenerated: 41; kept: 24.
- Would drop: Akki Roti, Avarekalu Usli, Banana Apple Mash, Banana Ragi Porridge, Beans Fry, Cauliflower And Red Bell Pepper Stir Fry, Classic Indian Sliced Salad, Curry Fried Quinoa Rice, Dill Cucumber Raita, Gojju Avalakki, Green Beans Fry, Green Moong Dal Curry, Hara Dhania Paratha, Jolada Roti, Kachumber Salad, Malabar Curry, Pacha Payir Kulambu, Pudina Pyaz Kachumber Salad, Rasam, Sabbasige Rasam, Semiya Upma, Steamed White Rice, Togarikalu Akki
- Would add: Beans Cauliflower Poriyal, Bell Saaru, Carrots Dill And Peanut Sadam, Creamy Beetroot And Potato Puree, Egg Lifafa Paratha, Hyderabadi Khatti Dal, Jeera Rice, Maharashtrian Masale Baath, Moong Dal Khichdi, No Onion No Garlic Sambar Rice, Ragi Oatmeal Kanji, Ridge Gourd Sabzi, Spring Onion Dosa, Sweet Potato And Bitter Gourd Kulambu, Tamarind Gojju, Thengai Saadam, Vegetable Sambar

### Patient 37 — Test Patient 037
Stored plan: 36 distinct dishes; regenerated: 42; kept: 25.
- Would drop: Aloo Bharta, Banana Apple Mash, Bengali Luchi, Chicken Biryani, Curd Rice With Carrots, Dahi Bowl, Moong Dal Khichdi, Mui Borok, Pudina Pyaz Kachumber Salad, Savoury Oatmeal Porridge, Steamed Chawal
- Would add: Adraki Rajma Masala, Bihari Kale Gram Roti, Buttered Peas Puree, Chingri Paturi, Greens Rava Puliyodharai, Hyderabadi Khatti Dal, Lachedar Kakdi Pyaz Kachumber, Maida Luchi, Murg Anardana, Paneer Butter Masala, Quinoa And Vegetable Saute, Rava Fried Prawns, Ridge Gourd Sabzi, Sattu Litti, Sweet Potato And Bitter Gourd Kulambu, Vegetable Raita, Verkadalai Sundal- Peanut Sundal

### Patient 38 — Test Patient 038
Stored plan: 43 distinct dishes; regenerated: 39; kept: 27.
- Would drop: Banana Apple Mash, Banana Ragi Porridge, Dal Palak, Dhokla, Dill Cucumber Raita, Gatte Ki Sabzi, Hara Dhania Paratha, Hyderabadi Khatti Dal, Kachumber Salad, Moong Dal Pani, Paneer Butter Masala, Plain Poha, Pudina Pyaz Kachumber Salad, Quick And Easy Bread Upma, Steamed Rice, Tindora Sambharo
- Would add: Banana Filos, Besan Pithla, Buttered Peas Puree, Dal Chawal, Hara Pyaz Paratha, Khichdi Roti ??????, Lachedar Kakdi Pyaz Kachumber, Potato Onion Cheela, Quinoa And Vegetable Saute, Savoury Oatmeal Porridge, Sindhi Kadhi, Vatana Tonak

### Patient 39 — Test Patient 039
Stored plan: 44 distinct dishes; regenerated: 38; kept: 28.
- Would drop: Chatpata Rajma Salad, Dal Palak, Garwhali Kafuli, Green Moong Dal Tadka, Hara Dhania Paratha, Hara Pyaz Paratha, Kachumber Salad, Menthe Kadubu, Mixed Vegetable Fry, Moong Dal, Oats Banana Apple Porridge, Palak Paneer, Phulka, Plain Poha, Rajma Masala, Sabbasige Soppu Dosa
- Would add: Curd Rice With Carrots, Lemon Rice, Masoor Dal, Moong Dal Pani, Paneer Masala Dosa -Paneer Bhurji Dosa, Paneer Wrap, Spinach Paneer Kofta, Spinach Rice, Vegetable Sambar, Ven Pongal

### Patient 40 — Test Patient 040
Stored plan: 45 distinct dishes; regenerated: 46; kept: 36.
- Would drop: Barnyard Millet Sweet Pongal, Carrots Dill And Peanut Sadam, Classic Indian Sliced Salad, Gawar Pods Fenugreek Vegetable, Gongura Pulihora, Kandi Pachadi, Mixed Vegetable Fry, Ragi Kanji, Raw Mango Raita
- Would add: Akki Roti, Egg Lifafa Paratha, Egg Scramble With Drumstick Leaves, Palak And Kala Chana Sukhi Sabzi, Paneer Masala Dosa -Paneer Bhurji Dosa, Pudalangai Milagu Kootu, Thotakura Pappu, Vegetable Sambar, Ven Pongal, Warm Red Lentil Salad With Goat Cheese

### Patient 41 — Test Patient 041
Stored plan: 45 distinct dishes; regenerated: 47; kept: 37.
- Would drop: Barnyard Millet Sweet Pongal, Basil Tincture, Curd Rice With Carrots, Karela Bhujia, Millet Khichdi, Oats Dhokla, Pesarattu Upma, Ragi Kanji
- Would add: Curd Oats, Gawar Pods Fenugreek Vegetable, Maida Luchi, Masoor Moong Phali Ki Dal, Methi Malai Matar, Mohura Pitha, Panchkuti Khichdi, Plain Poha, Sabbasige Soppu Dosa, Shak Bhaja

### Patient 42 — Test Patient 042
Stored plan: 41 distinct dishes; regenerated: 39; kept: 29.
- Would drop: Aloo Bharta, Bajra Roti, Dahi Bowl, Egg Curry, Keeme Ja Bhalla, Lemon Rice, Moong Dal Khichdi, Navrang Dal, Phulka, Rasam, Steamed Rice, Vegetable Raita
- Would add: Chicken Biryani, Chicken Pulao, Dal Dhokli, Dal Khichdi, Egg Lifafa Paratha, Makki Dhokla, Masoor Dal And Rajma Masala, Plain Bhakri, Ridge Gourd Sabzi, Spinach Rice

### Patient 43 — Test Patient 043
Stored plan: 38 distinct dishes; regenerated: 38; kept: 21.
- Would drop: Beetroot Loni Sponge Dosa, Besan Capsicum Ki Sabzi, Besan Chila Stuffed With Chatap Paneer, Bhindi Masala, Chickpea Potato, Chole Masala, Chole Semiya Pulao, Gavarfali Ki Sukhi Sabzi, Gawarfli Dry Vegetable, Hara Dhania Paratha, Hare Chane Ka Pulav, Kara Sevai, Panchkuti Khichdi, Ragi Dosa, Raw Mango Raita, Sarson Ka Saag, Sukhe Chole
- Would add: Aloo Jeera, Beans Fry, Dahi Methi Puri, Dill Cucumber Raita, Green Beans Fry, Green Chilli Sabzi, Hara Pyaz Paratha, Masoor Dal, Matar Poha, Mixed Millet Khichdi, Moong Dal Khichdi, Navrang Dal, Palak Chole, Quick And Easy Bread Upma, Ragi Oatmeal Kanji, Singhara Ato Chill, Vegetable Sambar

### Patient 44 — Test Patient 044
Stored plan: 36 distinct dishes; regenerated: 45; kept: 18.
- Would drop: Banana Apple Mash, Brinjal Poriyal Masala, Carrot Paruppu Usili, Cauliflower And Red Bell Pepper Stir Fry, Chow Chow Curry, Curd Rice With Carrots, Curry Fried Quinoa Rice, Dill Cucumber Raita, Drumstick Greens Sambar, Jowar And Vegetable Porridge, Menthe Kadubu, No Onion No Garlic Sambar Rice, Poosanikai Sambar, Pudina Pyaz Kachumber Salad, Quick And Easy Bread Upma, Rasam, Spinach Idli, Togarikalu Akki
- Would add: Andhra Vankaya Fry With Peanuts, Appam, Buttered Peas Puree, Creamy Beetroot And Potato Puree, Drumstick Spinach Fry With Moong Dal, Green Moong Dal Kootu, Greens Rava Puliyodharai, Hara Pyaz Paratha, Jolada Roti, Khichdi Roti ??????, Kollu Thogayal, Kovakkai Podi Curry, Lachedar Kakdi Pyaz Kachumber, Menthya Dose, Miriyala Charu, Mixed Vegetable Koora, Mulakootal, Mysore Bonda, Pacha Payir Kulambu, Paneer Masala Dosa -Paneer Bhurji Dosa, Peerkangai Thogayal, Sabsige Soppu Kootu, Senai Potato Fry, Spring Onion Dosa, Thengai Saadam, Thotakura Pappu, Yellow Cucumber Dal

### Patient 45 — Test Patient 045
Stored plan: 46 distinct dishes; regenerated: 51; kept: 35.
- Would drop: Aloo Poha, Basil Tincture, Bharbhara, Broken Wheat Upma, Curd Rice With Carrots, Curry Fried Quinoa Rice, Kara Sevai, Malabar Curry, Masala Couscous Pulao, Rice Kheer, Sada Dahi
- Would add: Beans Fry, Bengali Gram Dal, Bihari Kale Chana Ki Ghugni, Buttered Peas Puree, Dal Chawal, Doi Chira, Egg Scramble With Drumstick Leaves, Green Beans Fry, Hara Pyaz Paratha, Kandarappam, Lachedar Kakdi Pyaz Kachumber, Moong Dal Methi Ki Sabzi, Onion Raita, Quick And Easy Bread Upma, Sattu Litti, Watermelon Seeds Rice

### Patient 46 — Test Patient 046
Stored plan: 34 distinct dishes; regenerated: 45; kept: 23.
- Would drop: Bhindi Raita, Carrot And Capsicum Rice, Dal Chawal, Dal Palak, Kachcha Kela Masala Sabzi, Malvani Chicken, Moong Dal Khichdi, Onion Raita, Sindhi Dharan Ji Kadhi, Spicy Cabbage Rice, Tindora Sambharo
- Would add: Bajra Rotla, Bardoli Ki Khichdi, Besan Pithla, Egg Dosa With Cheesy Garlic Mayo, Goan Chana Ros, Keeme Ja Bhalla, Khajur And Pakora Raita, Matta Rice Peas Pulao, Murg Anardana, Mushroom Vindaloo, Oats Banana Apple Porridge, Palak And Kala Chana Sukhi Sabzi, Plain Dahi Raita, Pomfret Curry, Satsaagi, Sheganchi Amti, Steamed Rice, Tawa Paratha, Tendli Bhaji, Varan Bhat, Vatana Tonak, Warm Red Lentil Salad With Goat Cheese

### Patient 47 — Test Patient 047
Stored plan: 43 distinct dishes; regenerated: 39; kept: 17.
- Would drop: Aloo Matar Paneer, Beans Fry, Carrot And Capsicum Rice, Chatpata Rajma Salad, Chole Capsicum Masala, Chotti Aloor Dum, Dahi Bowl, Dahi Wale Paneer, Dal Chawal, Dal Khichdi, Dal Tadka, Green Beans Fry, Indori Poha, Kachumber Salad, Masoor Dal, Mixed Millet Khichdi, Moong Dal Methi Ki Sabzi, No Onion No Garlic Aloo Gajar Ki Sabzi, Oats Banana Apple Porridge, Onion Raita, Paneer Butter Masala, Plain Dahi, Potato Onion Cheela, Rajgira Paneer Paratha, Rock Toast, Spicy Cabbage Rice
- Would add: Anda Bhurji, Cabbage Bhurji, Cabbage Tomato Sabzi, Corn And Peas Curry, Dal Kabila, Egg Dosa With Cheesy Garlic Mayo, Kadhi Pakora, Matar Millet Pulao, Matta Rice Peas Pulao, Methi Turai, Moong Dal Khichdi, Palak Gobi Sabzi, Palak Kadhi, Paneer Kulcha, Parwal Masala, Phulka, Pumpkin Dal, Rajasthani Ghasela, Raw Mango Masoor Dal, Soyabean Pulao, Spinach Paneer Kofta, Stuffed Karela With Aloo

### Patient 48 — Test Patient 048
Stored plan: 48 distinct dishes; regenerated: 46; kept: 22.
- Would drop: Bachala Pappu, Beans Cauliflower Poriyal, Brinjal Poriyal Masala, Carrot And Capsicum Rice, Carrot Beans Poriyal, Carrot Paruppu Usili, Cauliflower And Red Bell Pepper Stir Fry, Chicken Changezi, Chow Chow Curry, Chow Chow Kootu, Curd Oats, Drumstick Greens Sambar, Egg Pulao, Kaddu Badam, Kakdi Koshimbir, Keerai Poriyal, Kothamalli Thogayal, Lentil Bread Buttermilk, Moong Dal Pani, Moong Dal Rasam / Retired Pappu Charu, No Onion No Garlic Aloo Gajar Ki Sabzi, Oats Banana Apple Porridge, Obbattu Saaru, Phulka, Sorakkai Kozhukattai Paal Kuzhambu, Togarikaayi Usli
- Would add: Beans Usili, Capsicum Masala Poriyal, Corn And Peas Curry, Dahi Bowl, Drumstick Dal, Dry Sweet Potato Thoran, Egg Dosa With Cheesy Garlic Mayo, Karatya Kismore, Karnataka Special Huli Tovve, Keerai Masiyal, Kesari Pittal, Konaseema Kodi Kura, Mangrasa, Matta Rice Peas Pulao, Milagu Sadam, Multigrain Roti, Murg Anardana, Pala Kottai Sambar, Plain Wheat Paratha, Prawn Drumstick Curry, Sakkaravalli Kizhangu Poriyal, South Indian One Pot Sambar Rice, Thotakura Pappu, Yellow Cucumber Pachadi

### Patient 49 — Test Patient 049
Stored plan: 37 distinct dishes; regenerated: 43; kept: 34.
- Would drop: Banana Ragi Porridge, Curry Fried Quinoa Rice, Moong Dal Khichdi
- Would add: Chana Methi Dal, Curd Oats, Dahi Methi Puri, Maharashtrian Masale Baath, Mixed Vegetable Filling, Mung Bean Sprouts Upkari, Steamed Chawal, Vegetable Sambar, Whole Wheat Roti

### Patient 50 — Test Patient 050
Stored plan: 50 distinct dishes; regenerated: 46; kept: 38.
- Would drop: Banana Apple Mash, Bharwa Baingan Aur Pyaaz Ki Sabzi, Chana Masala, Classic Indian Sliced Salad, Dali Thoy, Dill Cucumber Raita, Gujarati Kadhi, Hara Pyaz Paratha, Kandarappam, Millet Khichdi, Millet Paruppu Adai, Panchkuti Khichdi
- Would add: Egg Lifafa Paratha, Hyderabadi Khatti Dal, Maharashtrian Masale Baath, Makki Dhokla, Milagu Sadam, Mung Bean Sprouts Upkari, Paneer Masala Dosa -Paneer Bhurji Dosa, Vegetable Sambar

### Patient 51 — Test Patient
Stored plan: 38 distinct dishes; regenerated: 49; kept: 33.
- Would drop: Curd Rice With Carrots, Curry Fried Quinoa Rice, Dal Chawal, Millet Khichdi, Moong Dal Khichdi
- Would add: Banana Apple Mash, Chickpea Potato, Cranberry Naan, Dill Cucumber Raita, Greens Rava Puliyodharai, Hara Dhania Paratha, Moong Dal, Multani Kaali Arbi, Navrang Dal, Onion Raita, Pahari Aloo Palda, Paneer Kulcha, Phulka, Pudina Pyaz Kachumber Salad, Shimla Mirch Ki Launji, Spiced Khooba Roti

### Patient 53 — Priya Test
Stored plan: 42 distinct dishes; regenerated: 46; kept: 12.
- Would drop: Avarekalu Usli, Bele Dose, Buckwheat Dosa, Chana Methi Dal, Classic Indian Sliced Salad, Cucumber Raita, Curd Oats, Curry Fried Quinoa Rice, Dahi Bowl, Dal Bharta, Dal Chawal, Dali Thoy, Foxtail Millet Paruppu Adai With Keerai, Green Moong Dal Kootu, Hara Dhania Paratha, Kachumber Salad, Kakdi Koshimbir, Kala Chana Masala Curry, Karela Bhujia, Kollu Thogayal, Masala Chaas, Millet Khichdi, Millet Paruppu Adai, Mixed Millet Khichdi, Plain Bhakri, Plain Dahi, Plain Dahi Raita, Ragi Sankati, Rajgira Paneer Paratha, Rajma Chawal
- Would add: Aloo Baingan, Andhra Steel Kandi Attu, Cabbage Soya, Chickpea Potato, Cranberry Naan, Creamy Beetroot And Potato Puree, Crispy Vegetable, Dahi Methi Puri, Gorai Kai Kara, Green Chilli Sabzi, Greens Rava Puliyodharai, Hara Pyaz Paratha, Hyderabadi Khatti Dal, Karatya Kismore, Kothavarangai Poriyal, Lacha Onion, Makki Dhokla, Masoor Dal And Rajma Masala, Medu Vada, Methi Pakoda Kadhi, Milagu Ven Pongal, Mung Bean Sprouts Upkari, Pahari Aloo Palda, Paneer Kulcha, Paneer Makhani, Phulka, Rajasthani Dal, Spiced Khooba Roti, Steamed Chawal, Steamed Rice, Sweet Potato And Bitter Gourd Kulambu, Tawa Paratha, Vegetable Sambar, Whole Wheat Roti

