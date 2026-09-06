# Team communications — September 2026

## Sent to Csenge

Hi Csenge,

Quick update on Fear HRI:

Local fear model is done and on GitHub: https://github.com/fahradnamazov-ops/fear_mecanumbot

You already tested the scripts — thanks, outputs looked correct. The pytest line failed because pytest needs pip install -r requirements.txt in that repo (fixed in the latest push).

HRI integration drafts are in my repo (ros_draft, sim_draft, notes/SIM_INTEGRATION.md). I don't have write access to mecanumbot_behaviours or Fortuz/mecanumbot, so nothing was pushed there. You can pull from my GitHub when you integrate sim.

Fahrad

Csenge reply (summary): AI lab accepted as done. Sim packages live under mecanumbot_remote/mecanumbot_sim.

## Sent / optional for Reha

Hey Reha,

Thanks for pointing me to mecanumbot_RL — that makes sense for sim/RL.

My fear code is in https://github.com/fahradnamazov-ops/fear_mecanumbot for now (local training + integration drafts). I'll align with mecanumbot_RL when we hook into sim — no rush on my side.

Fahrad

## Trello — Create fear model

GitHub: https://github.com/fahradnamazov-ops/fear_mecanumbot

Done:
- Fear dynamics + reward + biology mapping
- Local RL env + Q-learning; residual gap ~0.47; 50 tests
- Integration drafts (ros_draft, sim_draft)

Open / later:
- Full HRI on team sim (optional; AI lab accepted)
- Reiterate after feedback
- Ethologists when Csenge schedules
