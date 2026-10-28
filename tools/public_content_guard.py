#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ALLOWED_STATIC = {
    ".github/workflows/gamepulse-igp-oct27-seven-part-original-xyz-recovery.yml",  # authentic 7-part SHA private NBA original XYZ recovery only, public counts, never source positions
    ".github/workflows/gamepulse-igp-unified-56-private-query-qa.yml",  # private-original SHA-checked unified query only, public aggregate status, no coordinates

    ".github/workflows/gamepulse-igp-unified-56-season-tracking.yml",  # private NBA XYZ / models / Blueprint SHA verification and unified private QA only; public counts and status, no private XYZ
    ".github/workflows/gamepulse-igp-blueprint-official-56-qa.yml",  # SHA-only NBA public Blueprint shots versus private official PBP aggregate QA
    ".github/workflows/gamepulse-ippt-oct27-blueprint-backfill.yml",  # NBA public original shot report to private research branch only
    ".github/workflows/gamepulse-official-pbp-post36-backfill.yml",  # official public NBA PBP/box bytes committed private with final-score QA
    ".github/workflows/gamepulse-companion-original-0129-pilot.yml",  # bounded unauthenticated source GET; original bytes private release, public status only
    ".github/workflows/gamepulse-pr776-rockets-companion-z-variant-qa.yml",  # private SHA-verified NBA original SDK keyframe variant aggregate QA only; never public XYZ or licensed source artifacts
    ".github/workflows/gamepulse-ippt-public-web-app-shot-response-discovery.yml",  # first-party NBA public web endpoint structural shot-field check only; no auth, cookies, query URLs, raw payloads
    "tools/licensed_feed/public_web_shot_response_probe.mjs",  # first-party NBA public web endpoint structural shot-field check only; no auth, cookies, query URLs, raw payloads
    ".github/workflows/gamepulse-ippt-app-shot-details-0022600129-blueprint.yml",  # official public NBA Blueprint DET-NYK screenshot exact-shot attribute and precision check, private report
    ".github/workflows/gamepulse-ippt-app-shot-transmit-original-0125.yml",  # original authenticated private GamePulse EaseLive SDK shot-event JSON schema (structure only)
    ".github/workflows/gamepulse-ippt-public-stat-release-gate-2026.yml",  # no original NBA XYZ; private QA-driven public-stat fail-closed publication gate
    ".github/workflows/freeview-amen732-six-camera-real-native-synced-video.yml",  # six original NBA source cameras, UHD output to private 104 only
    "tools/amen732_sixview_synchronous_video_review_v1.py",  # ephemeral native source exact 4K mosaic, private output only
    ".github/workflows/freeview-amen732-original-vs-reacquired-source-sha.yml",  # compare six original NBA private release native MP4 identities, SHA-only
    ".github/workflows/freeview-amen732-private-synced-panel-review-readback.yml",  # private already SHA-verified source panel preview, no public source frames
    ".github/workflows/freeview-amen732-sixview-audio-corrected-contact-sheet.yml",  # SHA original six source feeds, private 4K native panels only
    "tools/amen732_sixview_native_frame_package_v2.py",  # ephemeral source original native PNG crops, no public pixels
    ".github/workflows/freeview-amen732-sixview-physical-sync-audit.yml",  # six native MP4 audio/timing audit: NO licensed media in public artifact
    "tools/amen732_sixview_audio_alignment_v2.py",  # hashed source manifest and source timestamp only
    ".github/workflows/gamepulse-ippt-clock-ten-model-all36.yml",  # private exact original NBA gameclock ten-player and ball model materialized, public aggregate QA only
    ".github/workflows/gamepulse-ippt-official-clock-model-real-2games.yml",  # private exact SHA NBA official ten full XYZ model physical-time query pilot aggregate QA
    ".github/workflows/gamepulse-ippt-official-gameclock-ten-36.yml",  # private original NBA official ten gameclock model source bracket QA, aggregate only
    ".github/workflows/gamepulse-ippt-running-gameclock-source-36.yml",  # private NBA official clock-progressing source coverage, no source player XYZ public
    ".github/workflows/gamepulse-ippt-possession-searchability-36.yml",  # private NBA source original PBP chain-searchability denominator QA; aggregate counts only
    ".github/workflows/gamepulse-ippt-model-b-native-graded-tiers-all36.yml",  # private source SHA G4 ten actor tiered ModelB coverage and ball aggregate QA only
    ".github/workflows/gamepulse-ippt-model-b-native-all36-private.yml",  # private SHA original NBA G4 source Model B overlay all36 actual performance/coverage, aggregate logs only
    "tools/amen732_native_sixvideo_fusion_mp4.py",  # reviewed original NBA event-732 direct six-view model-only research
    "tools/amen732_da3_unposed_sixview_trial.py",  # reviewed original NBA event-732 direct six-view model-only research
    "tools/amen732_native_six_video_frame_sets.py",  # reviewed original NBA event-732 direct six-view model-only research
    "tools/amen732_official_sixvideo_acquire.py",  # reviewed original NBA event-732 direct six-view model-only research
    ".github/workflows/freeview-amen732-direct-sixvideo-render.yml",  # reviewed original NBA event-732 direct six-view model-only research
    "tools/amen732_freeview_sixvideo_public_source.py",  # public NBA source ephemeral 6-video scene only; private MP4 sink
    ".github/workflows/freeview-amen732-sixvideo-public-reacquire.yml",  # official public source fallback with private result
    ".github/workflows/freeview-amen732-official-sixstream-source-probe.yml",  # Official public NBA six-stream probe; no private release or artifacts
    ".github/workflows/freeview-amen732-release-auth-bypass-probe.yml",  # private source access over direct release CDN, no public data
    ".github/workflows/freeview-amen732-six-original-videos-merged-private.yml",  # six private NBA source clips ephemeral, UHD merged MP4 private release only
    ".github/workflows/freeview-amen732-six-native-video-fusion.yml",  # private-only six-MP4 3D fusion and MP4 output
    ".github/workflows/gamepulse-ippt-source-ten-coverage-all36.yml",  # private SHA G4 native source-anchored ten plus ball outside official roster G2; aggregate QA only
    ".github/workflows/gamepulse-ippt-empty-chain-source-lag-tiers-36.yml",  # original NBA G4 SHA exact scorer-UTC nearest source lag tier for 129 unresolved chains private QA, public aggregates only
    ".github/workflows/freeview-amen732-da3-private-qa-readback.yml",  # SHA-verifies DA3 release results and commits only to private 104
    ".github/workflows/gamepulse-ippt-native-409-chain-coverage-36.yml",  # original NBA G4 36-game SHA source per-slot, ball, all-native chain-second and empty-chain aggregate private QA; public counts only
    ".github/workflows/freeview-amen732-da3-private-unposed-cpu.yml",  # private-only six-view CPU inference; model/source/output not published in public repo
    ".github/workflows/gamepulse-ippt-full-native-possession-v1-integration.yml",  # original 36-game G4 full native + v3 PBP source private read-only QA only; no private XYZ or actor IDs public
    ".github/workflows/gamepulse-ippt-all-event-sqlite-private-git.yml",  # private Git transport persist original NBA XY SQLite to separate private branch
    ".github/workflows/gamepulse-ippt-all-event-sqlite-private-release.yml",  # publish original NBA actor XY DB to PRIVATE repo release only; no public artifacts
    ".github/workflows/gamepulse-ippt-all-event-sqlite-private.yml",  # original all-action NBA source XY private-only SQLite, public count QA only
    ".github/workflows/gamepulse-ippt-private-v3-event-source-physics-sqlite.yml",  # private licensed original NBA PBP candidate XY + video-unverified moments only
    ".github/workflows/gamepulse-ippt-all-event-motion-v3-query-qa.yml",  # all22k private PBP XY/causal/motion readonly search full-index QA
    ".github/workflows/gamepulse-ippt-all-event-source-motion-v3-private.yml",  # exact SHA private NBA PBP original XY source candidate SQLite, no public binary
    ".github/workflows/gamepulse-ippt-native-event-physics-source-36.yml",  # original NBA shot and rebound source time candidate research only; no private XYZ in public logs
    ".github/workflows/gamepulse-ippt-private-v2-native-xy-causal-sqlite.yml",  # private original PBP native XY v2 causal graph immutable v1 + private DB
    ".github/workflows/gamepulse-ippt-all-pbp-causal-bundles.yml",  # PBP source all event scorer UTC causal graph aggregates only
    ".github/workflows/gamepulse-ippt-rebound-fourway-native-crosscheck.yml",  # all36 original NBA rebound native label/PBP/ball/official ten private-aggregate QA
    ".github/workflows/gamepulse-ippt-native-lasttouch-all-pbp-36.yml",  # original SHA native fresh label PBP actor identity aggregate crosscheck
    ".github/workflows/gamepulse-ippt-all10-rebound-contrastive-36.yml",  # source-only original NBA ball/official ten rebound rank aggregate diagnostics
    ".github/workflows/gamepulse-ippt-rebound-control-source-hypothesis.yml",  # private SHA original nonshot physics / wrong actor control aggregate only
    ".github/workflows/gamepulse-ippt-sdk-native-clock-schema.yml",  # exact SHA original SDK time/period metadata presence only; private source no values
    ".github/workflows/gamepulse-ippt-all-pbp-native-xy-36.yml",  # all22,314 original NBA PBP action XY read-only private SHA aggregate-only
    ".github/workflows/gamepulse-ippt-blueprint-shot-release-query.yml",  # exact NBA event source and published original Blueprint private aggregate QA
    ".github/workflows/gamepulse-ippt-blueprint-source-release-36-query.yml",  # SHA private NBA read-only event query aggregate acceptance only
    ".github/workflows/gamepulse-ippt-blueprint-pbp-shotchart-lineage-36.yml",  # SHA original public NBA PBP vs official Blueprint chart XY aggregate equality only
    ".github/workflows/gamepulse-ippt-blueprint-location-xy-30-holdout.yml",  # published Blueprint chart vs original shooter XY aggregate QA
    ".github/workflows/gamepulse-ippt-all36-original-sdk-actor-flags.yml",  # six shard original NBA SDK actor native event flag QA
    ".github/workflows/gamepulse-ippt-raw-sdk-event-interpolation-provenance.yml",  # source raw SDK per-actor interpolation flag QA
    ".github/workflows/gamepulse-ippt-native-pose-provenance-schema.yml",  # audited original NBA native pose and interpolation flags aggregate-only
    ".github/workflows/gamepulse-ippt-event-native-coordinate-masked-36.yml",  # original NBA shot event XY ball3D validation aggregate-only
    ".github/workflows/gamepulse-ippt-blueprint-geometry-definition.yml",  # original-source NBA event geometry QA only
    ".github/workflows/gamepulse-ippt-blueprint-common-delay-36.yml",  # source-only Blueprint event alignment aggregates
    ".github/workflows/gamepulse-ippt-blueprint-shot-release-query.yml",
    ".github/workflows/gamepulse-ippt-shot-release-30game-holdout.yml",  # vetted event QA workflow
    ".github/workflows/gamepulse-ippt-ball-shot-release-candidate.yml",  # private original ball-shooter shot-release source motion and aggregate Blueprint comparison only
    ".github/workflows/gamepulse-ippt-blueprint-event-offset-diagnostic.yml",  # private source scorer UTC offset consistency, aggregates only
    ".github/workflows/gamepulse-ippt-blueprint-event-geometry-36.yml",  # private official NBA Blueprint release-distance benchmark, aggregate summaries only
    ".github/workflows/gamepulse-ippt-event-source-holdout.yml",  # reviewed original source frame blackout: aggregate error only, no licensed native XYZ
    ".github/workflows/gamepulse-ippt-event-snapshot-query-qa.yml",  # reviewed private SHA NBA event-source query, aggregate QA only, no private original XYZ
    ".github/workflows/gamepulse-ippt-event-snapshot-36-census.yml",  # reviewed original NBA PBP event join: aggregate source/ID/timing only, no private XYZ
    ".github/workflows/gamepulse-ippt-v03-four-game-holdout.yml",  # reviewed 4 private SHA NBA source games, p95/errors only, never player XYZ
    ".github/workflows/gamepulse-pr776-four-foot-defended-release-gravity.yml",  # private-only accepted Blueprint four-foot contested shooting with SHA-verified Gravity QA
    ".github/workflows/gamepulse-ippt-halfcourt-challenger-v03.yml",  # reviewed original NBA source masked QA, aggregate error only never XYZ
    ".github/workflows/gamepulse-pr776-six-foot-defended-release-gravity.yml",  # private-only accepted shot releases filtered by Blueprint contest distance <=72 inches, QA private
    ".github/workflows/gamepulse-ippt-halfcourt-settled-v2.yml",  # reviewed private source 36-game aggregate only; licensed NBA XYZ never logged
    ".github/workflows/gamepulse-ippt-halfcourt-offense-defense-qa.yml",  # reviewed private SHA NBA source, aggregate only official five cardinalities, no XYZ
    ".github/workflows/gamepulse-ippt-halfcourt-dual-benchmark.yml",  # reviewed private SHA NBA source, only aggregated selector/coverage counts; no licensed XYZ public
    ".github/workflows/gamepulse-ippt-isolated-source-pilot.yml",  # reviewed private-only aggregate CPU workflow
    ".github/workflows/gamepulse-ippt-isolated-source-pilot.yml",  # reviewed IPPT SHA private-source only; public logs game-level aggregate counts and holdout error percentiles, no player XYZ
    ".github/workflows/gamepulse-pr776-release-contest-gravity-joined.yml",  # read-only private Blueprint/Gravity SQLite, private-only aggregate and per-shot CSV outputs
    ".github/workflows/gamepulse-pr776-official-nba-season-gravity.yml",  # source-qualified public NBA Gravity leaders only; private SQLite and QA never published here
    "public_nba_gravity_leaders_2026_27_current.json",  # direct NBA public gravityleaders response with source SHA; no private XYZ
    ".github/workflows/gamepulse-pr776-blueprint-shot-gravity-52.yml",  # reviewed private licensed Blueprint source + PBP, public aggregate counts only, SQLite/QA committed private
    ".github/workflows/gamepulse-pr776-G4-native-player-possession-36.yml",  # reviewed 36-game G4 private SHA native actor, ball, NBA PBP chain indexing; no original XYZ in public logs
    ".github/workflows/gamepulse-pr776-G2-source-actor-transition-index-36.yml",  # private original NBA SDK substitution source player clock index, SHA-only public metrics
    "worker_results/reed-0022600125-q2-0841-temporary-multiangle.json",  # reviewed no licensed SDK XYZ, signed HLS or tokens; NBA public event metadata only
    ".github/workflows/resolve-reed-20261026-camera-angles.yml",  # reviewed signed NBA HLS URLs and exception details removed from public output
    ".github/workflows/gamepulse-pr776-G2-direct-actor-sub-transition-36.yml",  # SHA original NBA SDK roster change-source player observation clock analysis, safe aggregate public logs
    ".github/workflows/gamepulse-pr776-G2-exact-ten-transition-UTC-36.yml",  # original SDK source ten identity transition vs NBA official substitution UTC, aggregate-only public output
    ".github/workflows/gamepulse-pr776-G2-substitution-actor-query-36.yml",  # reviewed original private NBA actor/ball G1 SHA readback and pre/post-substitution G2 alternative roster, only safe public counts
    ".github/workflows/gamepulse-pr776-G2-substitution-source-identity-attribution-36.yml",  # G2 SHA-frozen NBA official substitution-side raw actor classification, private aggregate only
    ".github/workflows/gamepulse-pr776-G2-nba-substitution-side-query-36.yml",
    ".github/workflows/gamepulse-pr776-G2-substitution-side-roster-36.yml",
    ".github/workflows/gamepulse-pr776-G2-clock-source-conflict-dossier-36.yml",  # reviewed G2 private SDK source ID-to-official-NBA PBP/lineup forensic dossier, aggregate counts only public
    ".github/workflows/gamepulse-pr776-G2-source-official-conflict-episodes-36.yml",  # reviewed: private original SDK actor vs NBA official roster conflict episode QA, aggregate-only public output
    ".github/workflows/gamepulse-pr776-G2-roster-query-readbacks-36.yml",  # reviewed: 36 game private official NBA PBP long-pair roster source/G1 SHA readbacks, aggregate-only public output
    ".github/workflows/gamepulse-pr776-G2-long-official-pbp-roster-36.yml",  # reviewed: private SHA-verified NBA PBP two-ended longer UTC roster candidate QA, public aggregate counts only, no XYZ
    ".github/workflows/gamepulse-pr776-original-actor-G1-provenance-all36.yml",  # approved all-36 private raw SDK per-actor SHA+interpolation provenance, only safe aggregate public logs
    ".github/workflows/gamepulse-pr776-original-actor-G1-provenance-pilot.yml",  # reviewed: two SHA-verified private NBA SDK source games, actor interpolation metadata only; no public XYZ or player IDs
    ".github/workflows/gamepulse-pr776-full-native-P0-acceptance-36.yml",  # reviewed: SHA-verified private original-source 36-game XYZ readback; aggregate-only public logs, private QA receipt
    ".github/workflows/gamepulse-pr776-official-ten-source-conflict-36.yml",  # reviewed: private 36-game source/official strict NBA ten conflict metadata only, no public player coordinates
    ".github/workflows/gamepulse-pr776-source-first-B-reconciliation-36.yml",  # reviewed: frozen accepted QA manifests only, 36-game SHA-accounting aggregates written private
    ".github/workflows/gamepulse-pr776-original-sdk-interpolation-lineage-36.yml",  # reviewed: 36 SHA-verified 13-part original private SDK archives, per-game QA only committed to private PR, public runner logs aggregate counts
    ".github/workflows/gamepulse-pr776-original-sdk-metadata-fidelity-rockets.yml",  # reviewed: exact 13 SHA-verified private NBA SDK tarballs, metadata-only private QA, never public raw coordinates
    ".github/workflows/gamepulse-pr776-source-first-atlas-36.yml",  # reviewed: private original SDK source read-only; public logs contain aggregate status/counts, SHA-pinned QA committed private-only
    ".github/workflows/gamepulse-pr776-natural-original-player-gaps.yml",  # reviewed: SHA-verified private player direct-gap distribution, aggregate only, original XYZ not in public logs
    ".github/workflows/gamepulse-pr776-c1-5-8-10s-benchmark.yml",  # reviewed: read-only SHA-verified private NBA XYZ withheld eval, aggregate results private-only; no player locations in public logs
    ".github/workflows/gamepulse-igp-fast-lineup-two-game-qa.yml",  # private-only source ten-ID anchors and guarded 2–5s masked XYZ holdout; no public source or artifacts
    ".github/workflows/gamepulse-rockets-official-utc-overlap-graph.yml",  # reviewed private-only PBP UTC overlap graph; no coordinates or public artifacts
    ".github/workflows/gamepulse-rockets-xfg-chain-source-qa.yml",  # reviewed private-only SHA-pinned Blueprint xFG to official logical-chain QA, aggregate public logs
    ".github/workflows/gamepulse-rockets-original-frame-gap-attribution.yml",  # reviewed private-only SHA-checked original frame-window diagnostic, aggregate public logs
    ".github/workflows/gamepulse-oct26-official-pbp-public.yml",  # official NBA PBP source-only, private repo write through existing GitHub token
    ".github/workflows/gamepulse-oct26-last3-parallel-parts.yml",  # bounded original NBA SDK live-ended parts; private-only releases
    ".github/workflows/gamepulse-oct26-incremental-catalog.yml",  # private complete-source 43-to-52 incremental catalog indexer
    ".github/workflows/gamepulse-igp-additive-original-source-index.yml",  # private additive original XYZ 36-to-52 source manifest; no public raw XYZ
    ".github/workflows/gamepulse-oct25-26-original-xyz-catchup.yml",  # private original SDK Oct25-26 official final batch; no public source or artifacts
    ".github/workflows/gamepulse-private-season43-integrity.yml",  # reviewed: private sparse-source SHA acceptance, aggregate-only logs
    "tools/gamepulse_private_43_integrity_acceptance.py",  # reviewed: local SHA checks of licensed private views, no public data
    ".github/workflows/gamepulse-official-20261025-seven.yml",  # reviewed: official NBA seven-game PBP and advanced source private-only publication; no public artifacts
    ".github/workflows/gamepulse-pr776-realutc-chain-xyz-query.yml",  # reviewed SHA-guarded NBA real UTC chain source lookup, private coordinates only
    ".github/workflows/gamepulse-pr776-wallclock-native-possession-query.yml",  # reviewed private 36-game source UTC/native interval QA, metadata-only public stdout and private-only output
    ".github/workflows/gamepulse-pr776-rebound-video-recovery.yml",  # manually inspected: exact one-event P2 private NBA Broadcast media, SHA-only public status, no upload-artifact, source remains private
    ".github/workflows/gamepulse-pr776-wallclock-season-index-36.yml",  # reviewed: SHA-pinned private original 36-game frames, no public coordinates or artifacts
    ".github/workflows/gamepulse-pr776-original-xyz-timeactual-chain-36.yml",  # reviewed private 36-game original SDK source-to-PBP UTC candidate QA only
    ".github/workflows/gamepulse-pr776-timeactual-wall-36.yml",  # reviewed private official 36-game NBA timeActual + native manifests, public counts only
    ".github/workflows/gamepulse-pr776-official-wall-time-acceptance.yml",  # reviewed official NBA timeActual plus private SDK UTC QA, aggregates only publicly
    ".github/workflows/gamepulse-pr776-broadcast-anchor-video-access.yml",  # reviewed NBA official event-video endpoint access, metadata QA only, no clips
    ".github/workflows/freeview-amen732-board-static-sources.yml",
    ".github/workflows/freeview-amen732-multipt-photo-refit.yml",
    ".github/workflows/gamepulse-pr776-direct-sdk-time-probe.yml",  # reviewed one-game private source SHA metadata schema only; never publish raw SDK coordinates/values
    ".github/workflows/gamepulse-pr776-unified-chain-xyz-v2.yml",  # private-only NBA XYZ source evidence
    ".github/workflows/gamepulse-pr776-direct-full-sdk-120-fallback.yml",  # private immutable original full SDK source fallback with aggregate logs
    ".github/workflows/gamepulse-pr776-chain-queryable-28-qa.yml",  # private SHA-verified aggregate original XYZ only
    ".github/workflows/gamepulse-pr776-chain-xyz-query-pilot.yml",  # private-only source-indexed 10-player/ball query; aggregate log without raw XYZ
    ".github/workflows/gamepulse-pr776-monotone-native-28game.yml",  # reviewed: private SHA-checked native NBA chain research, only aggregate public logs
    ".github/workflows/gamepulse-pr776-monotone-native-chain-pilot.yml",  # private source XYZ only in ephemeral CPU; aggregate candidate evidence in private repo; public logs counts only
    ".github/workflows/gamepulse-pr776-physical-nba-candidate-36.yml",  # reviewed: SHA-checked private official NBA PBP, candidate metadata only, no raw XYZ or public artifacts
    ".github/workflows/gamepulse-pr776-physical-native-36-continuity.yml",  # reviewed: private-only 36-game SHA continuity QA; aggregate counts only, no public source outputs
    ".github/workflows/freeview-amen732-right-above-rim-metric.yml",
    ".github/workflows/freeview-amen732-static-right-above-rim.yml",
    ".github/workflows/freeview-amen732-high-tight-third-view.yml",
    ".github/workflows/freeview-amen732-left-long-research-pts.yml",
    ".github/workflows/freeview-amen732-two-slash-extended-native.yml",
    ".github/workflows/gamepulse-pr776-original-xyz-search-audit.yml",  # reviewed: private-only SHA-verified XYZ CPU acceptance
    ".github/workflows/gamepulse-pr776-event-episode-crosswalk-test.yml",  # reviewed pinned private-only CPU acceptance, no source publication
    ".github/workflows/freeview-amen732-sam2-world-camera-holdout.yml",
    ".github/workflows/freeview-amen732-sam21-23-source-frames.yml",
    ".github/workflows/freeview-amen732-43xyz-23pixel-holdout.yml",
    ".github/workflows/freeview-amen732-q4-sdk-proof.yml",
    ".github/workflows/freeview-amen732-sam21-cpu-masks.yml",
    ".github/workflows/amen732-cotracker3-source-research.yml",
    ".github/workflows/freeview-amen732-ball-evidence.yml",
    ".github/workflows/gamepulse-original-raw-completeness.yml",  # reviewed: SHA-pinned original source read-only aggregate QA, no raw data publication
    ".github/workflows/gamepulse-pr776-original-sdk-terminal-xyz.yml",  # reviewed: one real private NBA SDK game, original SHA, aggregate-only logs
    ".github/workflows/gamepulse-pr776-rockets-spurs-native-advanced.yml",  # reviewed: CPU, private original NBA source and private-only source publish
    ".github/workflows/gamepulse-pr776-season-search-provider-acceptance.yml",  # reviewed ephemeral private NBA source retrieval and aggregate-only QA
    ".github/workflows/gamepulse-pr776-acceptance-20261025.yml",  # reviewed CPU-only pinned SHA private fetch; no public data outputs
    ".github/workflows/gamepulse-wemby-defensive-position.yml",  # CPU-only original NBA source, private source/aggregated results only
    ".github/workflows/clip-lab-event80-direct-native-frozen.yml",  # audited CPU-only original NBA source, private SDK, final ringed MP4
    ".github/workflows/clip-lab-rockets-event80-frozen-render.yml",  # reviewed: exact frozen source SHA and private-only v3.1 MP4
    ".github/workflows/clip-lab-event80-delivery-smoke.yml",  # test fixture artifact only
    ".github/workflows/clip-lab-rockets-event80-hls.yml",  # reviewed: exact one-event private HLS CPU staging only
    ".github/workflows/clip-lab-rockets-event80-native.yml",  # reviewed: exact event native SDK SHA extraction, private only
    ".github/workflows/clip-lab-rockets-event80-frozen-cpu.yml",  # reviewed: original CPU frozen v3.1 detector, private QA only
    ".github/workflows/clip-lab-encrypted-event86-handoff.yml",
    "tools/clip_lab_public_handoff_cert.pem",
    ".github/workflows/clip-lab-artifact-handoff-smoke.yml",
    ".github/workflows/freeview-amen-732-4k-contact-diagnostic.yml",
    ".github/workflows/clip-lab-adams86-original-frozen-cpu-full20.yml",
    ".github/workflows/clip-lab-event86-view-quality-cpu.yml",
    ".github/workflows/clip-lab-adams86-xfg-source-quality.yml",
    ".github/workflows/clip-lab-adams86-original-frozen-cpu-tracker-probe.yml",
    ".github/workflows/clip-lab-rockets-spurs-adams-86-video-sync.yml",
    ".github/workflows/clip-lab-rockets-spurs-adams-86-native-video.yml",
    ".github/workflows/freeview-amen-732-final-seconds-recovery.yml",
    ".github/workflows/rockets-spurs-q1-sdk-recovery.yml",
    ".github/workflows/gamepulse-unresolved-official-onoff-watch.yml",
    "tools/licensed_feed/pbpstats_missing_onoff_fallback.py",
    ".github/workflows/gamepulse-pbpstats-missing-game-fallback.yml",
    ".github/workflows/gamepulse-28game-source-assemble.yml",
    ".github/workflows/gamepulse-28game-possession-tracking-crosswalk.yml",
    ".github/workflows/gamepulse-native-interactions-season-missing13.yml",
    ".github/workflows/gamepulse-two-game-chronology-acceptance.yml",
    ".github/workflows/gamepulse-universal-alignment-acceptance.yml",  # private-only CPU gate; universal source/clock/possession QA
    ".github/workflows/gamepulse-video-free-clock-season.yml",  # source-only daily CPU backfill; no video, no public player assets
    ".github/workflows/gamepulse-nba-official-advanced-ratings.yml",
    ".github/workflows/clip-lab-rockets-event80-hls.yml",
    ".github/workflows/gamepulse-native-interactions-partial-aggregate.yml",
    ".github/workflows/gamepulse-season-query-coverage-tests.yml",
    ".github/workflows/gamepulse-quarantined-native-labels.yml",
    ".github/workflows/gamepulse-unattributed-native-source.yml",
    ".github/workflows/gamepulse-unified-native-search.yml",
    ".github/workflows/gamepulse-native-interactions-0095-blueprint-quarantine.yml",
    "tools/licensed_feed/official_pbp_onoff_28.py",
    ".github/workflows/gamepulse-28game-native-pbp-onoff.yml",
    ".github/workflows/rockets-wemby-opponent-ppp.yml",
    ".github/workflows/freeview-amen-732-private-visual-panels.yml",
    ".github/workflows/freeview-amen-732-private-audio-sync.yml",
    ".github/workflows/freeview-amen-732-private-native.yml",
    ".github/workflows/gamepulse-season-backlog.yml",
    ".github/workflows/gamepulse-20261024-final-fastlane.yml",
    ".github/workflows/gamepulse-rockets-spurs-fusion-merge.yml",
    ".github/workflows/gamepulse-rockets-spurs-original-qa.yml",
    "tools/licensed_feed/verify_gameplay_0009.py",
    "tools/licensed_feed/audit_sdk_metadata_0009.py",  # original private SHA-only schema inventory; no licensed values published
    ".github/workflows/public-nba-gravity-onegame.yml",
    ".github/workflows/nba-blueprint-priority-private-acquire.yml",
    "public_nba_gravity_rockets_game1_2026_27.json",
    "README.md",
    "PUBLIC_CONTENT_POLICY.md",
    "runner_policy.json",
    "bridge_consumer_heartbeat.json",
    "bridge_consumer_receipt.json",
    "bridge_execution_status.json",
    "bridge_result_summary.json",
    "tools/public_bridge_preflight.py",
    "tools/wait_for_consumer_receipt.py",
    "tools/public_content_guard.py",
    ".github/workflows/gamepulse-github-private-pilot.yml",
    "tools/licensed_feed/browser.js",
    "tools/licensed_feed/capture.mjs",
    "tools/licensed_feed/capture.test.mjs",
    "tools/licensed_feed/github_private_release.mjs",
    "tools/licensed_feed/github_private_release.test.mjs",
    "tools/licensed_feed/live_discovery.mjs",
    "tools/licensed_feed/live_discovery.test.mjs",
    "tools/licensed_feed/index.html",
    "tools/licensed_feed/package.json",
    "tools/licensed_feed/season_core.mjs",
    "tools/licensed_feed/season_core.test.mjs",
    "tools/licensed_feed/sdk_slot.mjs",
    "tools/licensed_feed/sdk_slot.test.mjs",
    "tools/licensed_feed/season_private_release.mjs",
    "tools/licensed_feed/verify_gameplay.py",
    ".github/workflows/gamepulse-gameplay-audit.yml",
    ".github/workflows/gamepulse-defender-spacing-qa.yml",
    ".github/workflows/gamepulse-rockets-private-clip-pilot.yml",
    ".github/workflows/nba-ring-only-private-pilot.yml",
    ".github/workflows/nba-jabari616-camera-qa.yml",
    ".github/workflows/nba-jabari616-frozen-ring-cpu-qa.yml",
    ".github/workflows/nba-jabari616-constant-ring-render.yml",
    ".github/workflows/nba-jabari616-constant-ring-v2.yml",
    ".github/workflows/nba-jabari616-ring-export-to-chat.yml",
    ".github/workflows/nba-jabari616-ball-handler-media.yml",
    ".github/workflows/nba-jabari616-cumulative-five-rings.yml",
    ".github/workflows/nba-jabari616-frozen-v31-quality.yml",
    ".github/workflows/nba-jabari616-frozen-v31-efficient.yml",
    ".github/workflows/nba-jabari616-frozen-v31-pulse-dense.yml",
    ".github/workflows/nba-jabari616-cumulative-play12.yml",
    ".github/workflows/nba-jabari616-five-ring-public-preview.yml",
    ".github/workflows/nba-jabari616-frozen-v31-public-video.yml",
    ".github/workflows/nba-jabari616-cumulative-receivers.yml",
    ".github/workflows/gamepulse-pnr-feasibility.yml",
    ".github/workflows/rockets-pnr-unified-review-qa.yml",
    ".github/workflows/rockets-pnr-video-source-diagnostic.yml",
    ".github/workflows/rockets-pnr-0075-gamepulse-review.yml",
    ".github/workflows/rockets-all-defensive-pnr-analysis.yml",
    ".github/workflows/gamepulse-pnr-ui-preflight.yml",
    ".github/workflows/gamepulse-github-season.yml",
    ".github/workflows/gamepulse-live-cle-phi-20261022.yml",
    ".github/workflows/gamepulse-cavs-native-seek-diagnostic.yml",
    ".github/workflows/gamepulse-live-all-games.yml",
    "tools/licensed_feed/live_capture_cycle.mjs",
    "tools/licensed_feed/live_capture_cycle.test.mjs",
    "tools/licensed_feed/live_discovery.mjs",
    "tools/licensed_feed/live_discovery.test.mjs",
    ".github/workflows/gamepulse-final-fastlane.yml",
    ".github/workflows/gamepulse-rockets-finalize-safeguard.yml",
    ".github/workflows/gamepulse-20261022-slate-backfill.yml",
    ".github/workflows/gamepulse-20261022-targeted-retry.yml",
    ".github/workflows/gamepulse-source-ready-final10.yml",
    ".github/workflows/gamepulse-part6-fast.yml",
    ".github/workflows/gamepulse-14game-world-source-qa.yml",
    ".github/workflows/gamepulse-private-search-index.yml",
    ".github/workflows/gamepulse-16game-private-search.yml",
    ".github/workflows/gamepulse-denver-sdk-recovery.yml",
    ".github/workflows/gamepulse-denver-official-pbp.yml",
    ".github/workflows/gamepulse-16game-coverage-qa.yml",
    ".github/workflows/gamepulse-denver-source-ready-retry.yml",
    ".github/workflows/gamepulse-private-blueprint-fusion.yml",
    ".github/workflows/gamepulse-2026-source-evidence.yml",
    ".github/workflows/gamepulse-official-onoff-qa.yml",
    ".github/workflows/gamepulse-formal-pbp-14game.yml",
    ".github/workflows/rockets-three-player-touch-probe.yml",
    ".github/workflows/rockets-native-touch-ppp.yml",
    ".github/workflows/gamepulse-native-interactions-14game.yml",
    ".github/workflows/gamepulse-interaction-query.yml",
    "tests/test_consumer_receipt_waiter.py",
    "tests/test_public_bridge_preflight.py",
    "tests/test_public_content_guard.py",
    ".github/workflows/run.yml",
    ".github/workflows/public-bridge-preflight-tests.yml",
    ".github/workflows/public-content-guard.yml",
    ".github/workflows/validate-public-bridge.yml",
    ".github/workflows/oneoff-sanitize-history.yml",
    ".github/workflows/post-sanitize-public-audit.yml",
    ".github/workflows/dispatch-oidc.yml",
}
# These already-public, manually inspected CPU-only workflow definitions are
# pinned to exact Git blobs. New or edited workflows must be re-reviewed;
# the pin does not authorize source datasets, binaries or public results.
REVIEWED_WORKFLOW_GIT_BLOB_SHA = {
    ".github/workflows/reed-0022600125-exact-action.yml": "1f039e96c534a7ea842e3053b6eb3b3d8fed041e",  # reviewed manual-only official public PBP, no signed media retrieval/persistence
    "reed_0022600125_official_action.json": "935a9ebcbe4177b8d642065e9392fc4f5952b069",  # immutable public NBA action metadata; hls_options empty, no signed URL
    ".github/workflows/gamepulse-pr776-oreb-control-stress.yml": "04e268929cca1ccdd2aa3f8428704000b3ab41f1",  # private original SDK read, aggregate control diagnostic only
    ".github/workflows/gamepulse-pr776-position-holdout-36.yml": "f9cec9925acde87472678c4695c6715068c73685",  # original private XYZ source, aggregate position error only
    ".github/workflows/gamepulse-pr776-new-eight-original-qa.yml": "3bd7f6f2a15a25048549a0fb74c362d8f650885f",  # original 13-part SDK, aggregate QA private only
    ".github/workflows/freeview-amen732-board-static-sources.yml": "70af49120ab48235cf4e4463f96b73026ce555c7",
    ".github/workflows/freeview-amen732-multipt-photo-refit.yml": "2e0dad12a628d892fdaddbdbc971e103f6119f48",  # original NBA private six-anchor + full 3PT photometric heldout, no public RGB
    ".github/workflows/gamepulse-pr776-sdk-metadata-0009.yml": "d1c768ec93f6f761b8245de8d21df58abf7257b0",  # reviewed private-only original SDK field-key QA; no values/XYZ in public
    ".github/workflows/gamepulse-igp-eight-native-raw-backfill.yml": "7a9790609ce84fb8c108c0bccb6b33954c886ae5",  # source chunks remain private
    ".github/workflows/gamepulse-igp-full-native-season-coverage.yml": "a2f69e668372cb88816c7ad2fa9cf0fcb9c14828",  # SHA-only private coverage and no public artifacts
    ".github/workflows/gamepulse-igp-full-native-batch.yml": "f9d1c67b8e6dfdd25be96e68aa95c5e8021a0615",  # private-only original SDK XYZ batch
    ".github/workflows/gamepulse-igp-private-release-browser-download-smoke.yml": "63cd4be67c16b15a078cb864741b0d6ad7fe96be",  # reviewed single part no-REST browser route probe, digest-gated no public artifacts
    ".github/workflows/gamepulse-igp-original-sdk-remaining-seven-recovery.yml": "d8ab67ad7eeb527c9ba56350918233d626ec41c6",  # private original 13-part SHA assets, native-only QA, never public licensed XYZ
    ".github/workflows/gamepulse-igp-all-native-rockets.yml": "984864df90f937a4f478c327d8fc5de4a2575f2a",  # source XYZ private only
    ".github/workflows/gamepulse-igp-sdk-native-full-game-0104.yml": "45f1b8ebbb00f506d2600debd81c8592bfc0f7cd",  # 13 original SHA-pinned private archives, aggregate-only logs and private QA
    ".github/workflows/gamepulse-igp-private-sdk-asset-direct-probe.yml": "afd02dfbf261b09217f8c25fcd787a53335e5665",  # exact SHA-pinned private one-part asset integrity-only probe; no artifact publication
    ".github/workflows/gamepulse-igp-oreb-clock-update-gates.yml": "4685c26a97bf41d305cb4df083780bfec25d96fc",  # private-only NBA event and clock queue, no public source data
    ".github/workflows/gamepulse-igp-original-xyz-continuity-clock-review.yml": "f7bcf3fecf79e15be5602a80725e5605e0f900db",  # no source/public XYZ; SHA-verified per-episode aggregated private QA
    ".github/workflows/gamepulse-pr776-possession-first-36-materialize.yml": "274e3640860a303d74da3fa79354bd54af6ea8ea",  # private-source-only 36-game materialization; no public artifacts or source records
    ".github/workflows/gamepulse-pr776-fresh-touch-successor-context.yml": "ebd5147288f91936b583a84dd0f17c82dfcfd01b",  # reviewed private-only 93 candidate NBA context CPU with no public artifacts
    ".github/workflows/freeview-amen732-right-above-rim-metric.yml": "75667982d792310e56dca5f31d70492563a2e5cf",  # original NBA gamepulse world stable court KRT trial, private heldout and UHD QA
    ".github/workflows/freeview-amen732-static-right-above-rim.yml": "1b1cb13cede4778be8f697b8211db425dbd4ad58",  # original static right-above-rim private NBA court-source geometry and 4K QA
    ".github/workflows/freeview-amen732-high-tight-third-view.yml": "82d5b42a0ec14f47214c1257fecb44c40eab802e",  # exact SHA original High Tight third view, private-only 4K contact sheet
    ".github/workflows/freeview-amen732-left-long-research-pts.yml": "c79abf52f144b479452b8bc6fddd0cc55de32c00",  # Git-only private original NBA source; provisional PTS explicitly blocked for metric claims
    ".github/workflows/freeview-amen732-two-slash-extended-native.yml": "858e856f1b1a00718f1a4187c3860a1326c4cd42",  # source-native left/right Slash NBA clips, private-only 30fps contours
    ".github/workflows/gamepulse-pr776-original-xyz-search-audit.yml": "c3f846ddaacff6dbc4066e6dbf9a16d05bb4fff9",  # private authenticated Git; ephemeral source-only audit; aggregate logs
    ".github/workflows/gamepulse-pr776-event-episode-crosswalk-test.yml": "2e2c139ff6174c9927764513c423de89a31e3aa0",  # reviewed: private CPU-only exact-action tests, aggregate logs, no artifacts
    ".github/workflows/freeview-amen732-sam2-world-camera-holdout.yml": "649305ab47e78d343883e87e046bd5b2600559d7",  # private SAM2 native ball centroids and original world XYZ; aggregate-only public logs
    ".github/workflows/freeview-amen732-sam21-23-source-frames.yml": "242444981ff930b70f6a29e7bcc931a2efc42121",  # pinned Meta CPU, original 24 source NBA stills, private-only masks
    ".github/workflows/freeview-amen732-43xyz-23pixel-holdout.yml": "7fb576f1e6cc7803f4aad2d746eedb3ff3e570eb",  # original NBA SDK/X/Y/Z CPU holdouts; private-only coordinates and QA
    ".github/workflows/gamepulse-rockets-event-xyz.yml": "0814eefa14b62583095919d77b2368242d90cccb",  # reviewed: SHA-verified SDK, private XYZ output and aggregate public QA
    ".github/workflows/freeview-amen732-q4-sdk-proof.yml": "aaea8fd99cf84eca228d98aac079c21f822b348d",  # private original NBA 13-part SDK Q4 actor XYZ, no public export
    ".github/workflows/gamepulse-pr776-bulk-four-game-xyz.yml": "86bb20b96d0210becbc54c69c5b038b3adbb8074",
    ".github/workflows/gamepulse-pr776-bulk-0009-original-xyz.yml": "6306d60e989e0537c6469d49ab18bbed576d0846",
    ".github/workflows/pr776-shared-token-rate-diagnostic.yml": "d3c639f2f0aa6a3195e14a9aecbc2ce767bb646f",  # aggregate only; shared credential status, no SDK asset export
    ".github/workflows/gamepulse-pr776-native-event-windows.yml": "44cc1bded5419bbee63615ad5a4f493b89fb8f0d",  # reviewed private NBA/native guarded research windows no raw SDK coordinates
    ".github/workflows/gamepulse-pr776-private-event-xyz.yml": "b6d5fdbda5f2bd7c7aee13034119204027593b24",  # private-only SHA-verified SDK event subset; no coordinates in public logs
    ".github/workflows/gamepulse-pr776-event-first-36.yml": "9b011124c37e807ded708eb9ea720e2efb8cbe58",  # reviewed: private aggregate lookup and held-out position QA
    ".github/workflows/gamepulse-pr776-clock-shadow-study.yml": "844ff228aecad1a2537d4d986329e7b498d015bc",  # reviewed: private SHA-pinned clock QA, no raw source export or physical certification
    ".github/workflows/gamepulse-pr776-release-direct-pilot.yml": "5cd5cc5b299537a12f13a549e8f978b168a88b2a",  # reviewed private release download, no public artifact or coordinates
    ".github/workflows/gamepulse-video-free-clock-season.yml": "50f57ae8e3e6db0523dd25246110664b846441da",  # reviewed: original SHA-checked NBA SDK made-hoop QA only, private writes
    ".github/workflows/gamepulse-pr776-nba-36-episodes.yml": "edf6cce97c6db0d4b3775d172116813a6eb73aae",  # reviewed: private sparse source, full 36 SHA episode replay, old 28 preserved
    ".github/workflows/gamepulse-pr776-official-36game-expansion.yml": "a87ef5db6b672f78322fe49f4f9b46923cc17780",  # reviewed: private sparse git only; NBA official PBP/provider, 8-game addition, no public source files
    ".github/workflows/gamepulse-pr776-episode-season-search.yml": "e99e5e228ba930b89417cc80b7fd7a67a45a883b",  # reviewed: private aggregate-only 28-game episode QA index, no source XYZ publication
    ".github/workflows/gamepulse-pr776-official-native-xyz-bridge.yml": "bfff7805d3833a6d76beca6573a8e1a33aecc88a",  # reviewed: private 13-part SDK, source-independent tests, private-only aggregate XYZ QA
    ".github/workflows/gamepulse-official-lineup-clock-28.yml": "5e3ff52f3cf5825f4457c8dcea9ba72f828d7c28",  # reviewed: 28-game official PBP/provider CPU, private-only identities and aggregate public QA
    ".github/workflows/gamepulse-rockets-official-five-recovery.yml": "8f01ef993d7285ffce8c03e2ff2d1dc349f0b20e",  # reviewed: official NBA provider, private-only result; aggregate logs
    ".github/workflows/clip-lab-sengun-hawks-hls.yml": "cc7f972f9d51cc7aafe10fa71f0b395638bbed74",  # reviewed: NBA public event probe, metadata-only logs, no artifacts
    ".github/workflows/clip-lab-frozen-ring-sprites.yml": "a002f86a91280330248438f837bb2d5e7c51d99c",  # inspected: only generated RGBA ring sprites and metadata uploaded
    ".github/workflows/clip-lab-rockets-219-hls.yml": "16d9d45f0d718271049b894adbdf8375b9d22b5d",
    ".github/workflows/clip-lab-rockets-new-double-346-hls.yml": "330309713345d92819ebf61f46ca39fc7d7df969",
    ".github/workflows/clip-lab-rockets-new-double-353-hls.yml": "0fe06a115dd1f2c18c74a1be28753f1d63d41a44",
    ".github/workflows/clip-lab-rockets-new-double-616-hls.yml": "6b3185d4281a537492472914901102668bd409de",
    ".github/workflows/durant-context-inspection.yml": "90af2d117e4206b44861283e95e0c9440eca90d1",
    ".github/workflows/gamepulse-rockets-durant-double-review-v4.yml": "f396fc7957b5a49f8b9abb38bbb309a17b1c1c1a",
    ".github/workflows/gamepulse-rockets-event616-double-fn.yml": "8490170f6437241f4098bf6f0bd853ed91726149",
    ".github/workflows/gamepulse-rockets-sengun-double-4ft.yml": "2fd90ab0271963a3cfb9bf64336d50bbb0c78ab7",
    ".github/workflows/gamepulse-rockets-sengun-double-4ft-v2.yml": "0b870d0e02b71eebcee3bc3a890fe24530dfee68",
    ".github/workflows/gamepulse-rockets-sengun-double-relaxed-v3.yml": "0a6caf4914853cb8487468c092a01f7c7bd0279c",
    ".github/workflows/gamepulse-rockets-sengun-hub-qa.yml": "e9a8a41ab0d8b6ecf390d2fb847a8d2351765dbe",
    ".github/workflows/nba-jabari616-ball-handler-media.yml": "779830fa72713804709cc6455a91c702586c784b",
    ".github/workflows/nba-jabari616-pulse-frozen-ring-render.yml": "e0e9621b82a6da6f31bf27cbeb71232403fd346b",
    ".github/workflows/gamepulse-wemby-advanced-boxscore-0022600009.yml": "0aab6eb3a993d9d6a88776bad4a233029748c7ef",
    ".github/workflows/nba-jabari616-ring-export-to-chat.yml": "f63f723f34e03b12723389b1e84b3eb6de5b4e6e",
    ".github/workflows/rockets-durant-double-team-clip-verification.yml": "2d9573e710d1ad19e7ee68a202f35a8775cb4503",
    ".github/workflows/rockets-durant-reviewed-halfcourt-v5.yml": "bdb6e1d1062dff439c19ca85c8191c71a9aaecc8",
    ".github/workflows/rockets-remaining-sengun-double-clips.yml": "8f2a1d85f88845732f1139740eede73604cbde2c",
}

# Two reviewed, immutable handoff workflows may upload only their audited
# artifacts. In particular, the encrypted handoff's recipient certificate must
# also remain byte-for-byte pinned: changing the recipient would expose the
# private source bundle to an unintended decryptor.
REVIEWED_ARTIFACT_HANDOFF_GIT_BLOB_SHA = {
    ".github/workflows/clip-lab-artifact-handoff-smoke.yml": "c82cd5194d384e32acd1bf0cb42a0064e5703af7",
    ".github/workflows/clip-lab-encrypted-event86-handoff.yml": "4fb87ada769b0422c24afae0a60470c0d04bae3b",
}
REVIEWED_HANDOFF_CERT_GIT_BLOB_SHA = {
    "tools/clip_lab_public_handoff_cert.pem": "b3e84c69c35e061580dd3a4e6201c07f4adbdc19",
}

REVIEWED_PUBLIC_NBA_ACTION_METADATA = {
    ".github/workflows/reed-0022600125-exact-action.yml",
    "reed_0022600125_official_action.json",
}
REVIEWED_MEDIA_SOURCE_WORKFLOWS = {
    "tools/amen732_official_sixvideo_acquire.py",  # audited official NBA source page only, no signed URLs stored
    "tools/amen732_official_sixvideo_acquire.py",  # vetted native official HLS acquisition; never persists URLs or footage publicly
    ".github/workflows/freeview-amen732-direct-sixvideo-render.yml",  # public NBA stream source only; no native media artifacts
    "tools/amen732_freeview_sixvideo_public_source.py",  # only the public event page origin, no signed stream values committed
    ".github/workflows/freeview-amen732-official-sixstream-source-probe.yml",  # Official public NBA six-stream probe; no private release or artifacts
    ".github/workflows/clip-lab-sengun-hawks-hls.yml",  # pinned, public clips origin only; no raw URL output or artifacts
    ".github/workflows/clip-lab-rockets-219-hls.yml",
    ".github/workflows/clip-lab-rockets-new-double-346-hls.yml",
    ".github/workflows/clip-lab-rockets-new-double-353-hls.yml",
    ".github/workflows/clip-lab-rockets-new-double-616-hls.yml",
    ".github/workflows/rockets-durant-double-team-clip-verification.yml",
    ".github/workflows/rockets-remaining-sengun-double-clips.yml",
}
REVIEWED_PUBLIC_MP4_EXPORT_WORKFLOWS = {
    ".github/workflows/freeview-amen732-direct-sixvideo-render.yml",  # public NBA stream source only; no native media artifacts
    ".github/workflows/clip-lab-event80-direct-native-frozen.yml",  # one final QA-approved annotated MP4, never private source/tracking
    ".github/workflows/clip-lab-rockets-event80-frozen-render.yml",  # ONLY QA-approved ringed MP4 artifact
    ".github/workflows/clip-lab-event80-delivery-smoke.yml",  # harmless test fixture upload
    ".github/workflows/nba-jabari616-ball-handler-media.yml",
    ".github/workflows/nba-jabari616-ring-export-to-chat.yml",
    ".github/workflows/nba-jabari616-cumulative-receivers.yml",
}
# Reviewed immutable sprite export produces only generated RGBA PNG atlases and metadata;
# no source positions, tracking frames, or raw private SDK observations are uploaded.
REVIEWED_PUBLIC_SPRITE_EXPORT_WORKFLOWS = {
    ".github/workflows/clip-lab-frozen-ring-sprites.yml",
}
ALLOWED_PREFIXES = {"bridge_outbox/"}
FORBIDDEN_PREFIXES = {
    "experiments/",
    "experiment_results/",
    "prepared/",
    "models/",
    "checkpoints/",
    "fixtures/",
    "datasets/",
}
FORBIDDEN_EXT = {
    ".mp4", ".mov", ".mkv", ".avi", ".webm",
    ".pt", ".pth", ".onnx", ".engine", ".safetensors",
    ".csv", ".parquet", ".npz", ".npy", ".pkl", ".pickle",
}
TEXT_PATTERNS = [
    ("GCS_URI", re.compile(r"gs://", re.I)),
    ("SERVICE_ACCOUNT", re.compile(r"iam\.gserviceaccount\.com", re.I)),
    ("GCP_PROJECT_STYLE_ID", re.compile(r"\bproject-[a-z0-9][a-z0-9-]{4,}\b", re.I)),
    ("ACTIONS_ARTIFACT_UPLOAD", re.compile(r"actions/upload-artifact@", re.I)),
    ("DIRECT_PRIVATE_REPO_CHECKOUT", re.compile(r"repository:\s*[^\n]+/104\b", re.I)),
    ("MEDIA_SOURCE_URL", re.compile(r"(youtube\.com/watch|clips\.nba\.com)", re.I)),
]
REQUEST_RE = re.compile(r"^req-[0-9a-f]{32}$")

def tracked_files() -> list[str]:
    out = subprocess.check_output(["git", "ls-files", "-z"])
    return [x.decode() for x in out.split(b"\0") if x]

def violation(code: str, path: str) -> tuple[str, str]:
    return (code, path)

def scan(paths: list[str]) -> list[tuple[str, str]]:
    bad: list[tuple[str, str]] = []
    for rel in paths:
        p = Path(rel)
        if any(rel.startswith(prefix) for prefix in FORBIDDEN_PREFIXES):
            bad.append(violation("FORBIDDEN_PATH_CLASS", rel))
            continue
        if p.suffix.lower() in FORBIDDEN_EXT:
            bad.append(violation("FORBIDDEN_FILE_TYPE", rel))
            continue
        if rel not in ALLOWED_STATIC and rel not in REVIEWED_WORKFLOW_GIT_BLOB_SHA and not any(rel.startswith(prefix) for prefix in ALLOWED_PREFIXES):
            bad.append(violation("NOT_ALLOWLISTED", rel))
            continue
        if not p.is_file():
            continue
        pinned_sha = (
            REVIEWED_WORKFLOW_GIT_BLOB_SHA.get(rel)
            or REVIEWED_ARTIFACT_HANDOFF_GIT_BLOB_SHA.get(rel)
            or REVIEWED_HANDOFF_CERT_GIT_BLOB_SHA.get(rel)
        )
        if pinned_sha:
            current = subprocess.check_output(["git", "hash-object", rel], text=True).strip()
            if current != pinned_sha:
                bad.append(violation("REVIEWED_WORKFLOW_OR_CERT_CHANGED", rel))
                continue
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            bad.append(violation("NON_TEXT_FILE", rel))
            continue
        # The guard contains literal detection patterns by design; do not
        # flag its own source for defining those patterns.
        if rel != "tools/public_content_guard.py":
            for code, rx in TEXT_PATTERNS:
                # User-authorised publication of ONE rendered NBA clip, never
                # raw tracking or canonical private database records.
                if (code == "ACTIONS_ARTIFACT_UPLOAD" and
                    (rel in REVIEWED_PUBLIC_MP4_EXPORT_WORKFLOWS
                     or rel in REVIEWED_PUBLIC_SPRITE_EXPORT_WORKFLOWS
                     or rel in REVIEWED_ARTIFACT_HANDOFF_GIT_BLOB_SHA)):
                    continue
                # Existing exact-blob NBA clip locator workflows contain the
                # public clips.nba.com origin, never signed media URLs.
                if (code == "MEDIA_SOURCE_URL" and
                    (rel in REVIEWED_MEDIA_SOURCE_WORKFLOWS or
                     (rel in REVIEWED_PUBLIC_NBA_ACTION_METADATA and pinned_sha)) and
                    all(m.group(0).lower() == "clips.nba.com"
                        for m in rx.finditer(text))):
                    continue
                if rx.search(text):
                    bad.append(violation(code, rel))
    rid = Path("REQUEST_ID")
    if rid.exists():
        value = rid.read_text().strip()
        if value and not REQUEST_RE.fullmatch(value):
            bad.append(violation("SEMANTIC_OR_INVALID_REQUEST_ID", "REQUEST_ID"))
    return sorted(set(bad))

def main() -> int:
    bad = scan(tracked_files())
    if bad:
        for code, path in bad:
            print(f"PUBLIC_CONTENT_GUARD_FAIL code={code} path={path}")
        return 3
    print("PUBLIC_CONTENT_GUARD_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
