ic download --city [nome_cidade]
ic download --city [nome_cidade] --year [ano]
ic download --config config/[nome_cidade].yaml
ic preprocess --city [nome_cidade]
ic preprocess --city [nome_cidade] --year [ano]
ic structural --city [nome_cidade]
ic structural --city [nome_cidade] --year [ano]
ic paths --city [nome_cidade] --random
ic paths --city [nome_cidade] --year [ano] --random
ic centrality --city [nome_cidade] --top-k 30 --k-b 120 --k-e 60 --seed 42
ic functional-relations --city [nome_cidade]
ic validate-approximations --city [nome_cidade] --subgraph-size 400 --samples 10 30 60 120 --repeats 3 --seed 42
ic comparison-audit campinas jundiai sorocaba valinhos
ic historical-audit --reference campinas campinas_2010 campinas_2011 campinas_2012 campinas_2013 campinas_2014 campinas_2015 campinas_2016 campinas_2017 campinas_2018 campinas_2019 campinas_2020 campinas_2021 campinas_2022 campinas_2023 campinas_2024 campinas_2025 campinas_2026
ic centrality --city [nome_cidade] --year [ano] --top-k 30 --k-b 120 --k-e 60 --seed 42
ic communities --city [nome_cidade] --method greedy --min-size 30 --seed 42
ic communities --city [nome_cidade] --year [ano] --method greedy --min-size 30 --seed 42
ic inventory --city [nome_cidade]
ic inventory --city [nome_cidade] --year [ano]
ic dashboard --city [nome_cidade]
ic dashboard --city [nome_cidade] --year [ano]
ic compare [dataset_1] [dataset_2] [...dataset_n]
ic resilience --city [nome_cidade] --strategy targeted --max-fraction 0.15 --steps 15 --seed 42
ic resilience --city [nome_cidade] --year [ano] --strategy targeted --max-fraction 0.15 --steps 15 --seed 42
ic resilience --city [nome_cidade] --strategy targeted_adaptive --max-fraction 0.15 --steps 15 --seed 42
ic resilience --city [nome_cidade] --year [ano] --strategy targeted_adaptive --max-fraction 0.15 --steps 15 --seed 42
ic resilience --city [nome_cidade] --strategy random --max-fraction 0.15 --steps 15 --seed 42
ic node-resilience --city [nome_cidade] --strategy targeted --max-fraction 0.15 --steps 15 --k-node 80 --eff-samples 20 --seed 42
ic node-resilience --city [nome_cidade] --strategy targeted_adaptive --max-fraction 0.15 --steps 15 --k-node 80 --eff-samples 20 --seed 42
ic node-resilience --city [nome_cidade] --strategy random --max-fraction 0.15 --steps 15 --eff-samples 20 --seed 42
ic random-resilience-stats --city [nome_cidade] --mode both --seeds 42 43 44 45 46 --max-fraction 0.15 --steps 15 --k-edge 80 --k-node 80 --eff-samples 20
ic community-resilience --city [nome_cidade] --strategy targeted --max-fraction 0.30 --steps 15 --min-size 30 --seed 42
ic community-resilience --city [nome_cidade] --year [ano] --strategy targeted --max-fraction 0.30 --steps 15 --min-size 30 --seed 42
ic community-resilience --city [nome_cidade] --strategy targeted_adaptive --max-fraction 0.30 --steps 15 --min-size 30 --seed 42
ic community-resilience --city [nome_cidade] --year [ano] --strategy targeted_adaptive --max-fraction 0.30 --steps 15 --min-size 30 --seed 42
ic community-resilience --city [nome_cidade] --strategy random --max-fraction 0.30 --steps 15 --min-size 30 --seed 42
ic intra-community-resilience --city [nome_cidade] --strategy targeted --max-fraction 0.15 --steps 10 --min-size 2 --k-edge 40 --eff-samples 20 --seed 42
ic intra-community-resilience --city [nome_cidade] --year [ano] --strategy targeted --max-fraction 0.15 --steps 10 --min-size 2 --k-edge 40 --eff-samples 20 --seed 42
ic intra-community-resilience --city [nome_cidade] --strategy targeted_adaptive --max-fraction 0.15 --steps 10 --min-size 2 --k-edge 40 --eff-samples 20 --seed 42
ic intra-community-resilience --city [nome_cidade] --strategy random --max-fraction 0.15 --steps 10 --min-size 2 --eff-samples 20 --seed 42
ic vulnerability-index --city [nome_cidade] --top-k 100
ic structural-bottlenecks --city [nome_cidade] --top-k 100
ic route-redundancy --city [nome_cidade] --pairs 100 --threshold 1.50 --seed 42 --map-limit 20
ic spatial-multiscale --city [nome_cidade] --cell-size-m 1000
ic spatial-robustness --city [nome_cidade] --cell-size-m 1000 --mode incident --eff-samples 10 --max-eff-cells 100 --seed 42
ic road-hierarchy --city [nome_cidade] --eff-samples 20 --seed 42 --map-edges-per-class 1200
ic urban-morphology --city [nome_cidade] --cell-size-m 1000
ic od-efficiency --city [nome_cidade] --pairs 1000 --seed 42 --map-limit 80
ic subcenters --city [nome_cidade] --cell-size-m 1000 --percentile 0.90 --min-nodes 20
ic urban-barriers --city [nome_cidade] --cell-size-m 1000 --map-limit 250
ic network-scale-profile --city [nome_cidade] --scales 500 1000 2000 3000
ic city-similarity [dataset_1] [dataset_2] [dataset_3] --output-dir outputs/comparisons --min-coverage 1.0
ic report --city [nome_cidade]
ic report --city [nome_cidade] --year [ano]
