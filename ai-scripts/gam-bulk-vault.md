- Create CSV w/2 Columns. ExportName and Query
- ExportName is the name of each folder. Query is each individual search query.
- Upload the CSV to Cloud Shell
- Run Commands

Throttle to avoid rate limit

gam config num_threads 1 save

Leverages CSV to get a count from a specific user in a specific matter and outputs to another csv


echo "Query,Account,Count" > final_counts_clean.csv
while IFS=, read -r ExportName Query; do
  # Skip the header row
  if [[ "$ExportName" == "ExportName" ]]; then continue; fi
  
  echo -n "$Query," >> final_counts_clean.csv
  gam print vaultcounts matter "@ashtom lit hold" \
      corpus mail accounts "ashtom@github.com" \
      terms "$Query" \
      start "2018-01-01" \
      end "2025-11-15" | grep "ashtom@github.com" | awk '{print $1","$2}' >> final_counts_clean.csv
done < vault_tasks.csv
