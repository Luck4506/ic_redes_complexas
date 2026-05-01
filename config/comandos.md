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
ic centrality --city [nome_cidade] --year [ano] --top-k 30 --k-b 120 --k-e 60 --seed 42
ic communities --city [nome_cidade] --method greedy --min-size 30 --seed 42
ic communities --city [nome_cidade] --year [ano] --method greedy --min-size 30 --seed 42
ic resilience --city [nome_cidade] --strategy targeted --max-fraction 0.15 --steps 15 --seed 42
ic resilience --city [nome_cidade] --year [ano] --strategy targeted --max-fraction 0.15 --steps 15 --seed 42
ic resilience --city [nome_cidade] --strategy random --max-fraction 0.15 --steps 15 --seed 42
ic report --city [nome_cidade]
ic report --city [nome_cidade] --year [ano]
