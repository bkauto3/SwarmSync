const fs = require('fs');
const { createClient } = require('@supabase/supabase-js');

// Supabase credentials
const SUPABASE_URL = 'https://kolgqfjgncdwddziqloz.supabase.co';
const SUPABASE_SERVICE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtvbGdxZmpnbmNkd2RkemlxbG96Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NjczODc2MSwiZXhwIjoyMDcyMzE0NzYxfQ.xPoR2Q_yey7AQcorPG3iBLKTadzzSEMmK3eM9ZW46Qc';

// Initialize Supabase client
const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);

// Parse CSV manually (simple parser)
function parseCSV(text) {
  const lines = text.split('\n');
  const headers = parseCSVLine(lines[0]);
  const records = [];

  for (let i = 1; i < lines.length; i++) {
    if (!lines[i].trim()) continue;

    const values = parseCSVLine(lines[i]);
    if (values.length !== headers.length) {
      console.warn(`Skipping malformed line ${i + 1}`);
      continue;
    }

    const record = {};
    headers.forEach((header, index) => {
      let value = values[index];

      // Parse boolean values
      if (value === 'TRUE') value = true;
      else if (value === 'FALSE') value = false;
      // Parse null values
      else if (value === '' || value === 'NULL') value = null;
      // Parse numbers
      else if (header === 'domain_authority' || header === 'failure_rate' ||
               header === 'consecutive_failures' || header === 'total_submissions' ||
               header === 'successful_submissions' || header === 'failed_submissions' ||
               header === 'cost_amount' || header === 'tier_required' ||
               header === 'estimated_traffic' || header === 'time_to_approval_hours' ||
               header === 'priority_score') {
        value = value ? parseFloat(value) : null;
      }
      // Parse JSON fields
      else if (header === 'features' || header === 'field_selectors' ||
               header === 'selector_discovery_log' || header === 'field_constraints' ||
               header === 'category_options' || header === 'health_check_result' ||
               header === 'last_submission_attempt' || header === 'form_steps') {
        try {
          value = value ? JSON.parse(value) : null;
        } catch (e) {
          value = null;
        }
      }
      // Parse array fields
      else if (header === 'required_fields' || header === 'optional_fields' ||
               header === 'rejection_reasons' || header === 'niche_tags' ||
               header === 'geo_restrictions') {
        try {
          value = value ? JSON.parse(value) : [];
        } catch (e) {
          value = [];
        }
      }

      // Map submission_method values to match database constraint
      if (header === 'submission_method' && value === 'form') {
        value = 'web_form';
      }

      record[header] = value;
    });

    records.push(record);
  }

  return records;
}

function parseCSVLine(line) {
  const values = [];
  let current = '';
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    const nextChar = line[i + 1];

    if (char === '"' && inQuotes && nextChar === '"') {
      current += '"';
      i++; // Skip next quote
    } else if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === ',' && !inQuotes) {
      values.push(current.trim());
      current = '';
    } else {
      current += char;
    }
  }

  values.push(current.trim());
  return values;
}

async function syncDirectories() {
  try {
    console.log('Reading CSV file...');
    const csvContent = fs.readFileSync(
      'C:\\Users\\Ben\\Desktop\\Github\\Agent-Market\\456 TOTAL DIRECTORIES For Genesis.csv',
      'utf-8'
    );

    console.log('Parsing CSV data...');
    const records = parseCSV(csvContent);
    console.log(`Parsed ${records.length} records from CSV`);

    // Delete all existing records
    console.log('\nDeleting existing records from directories table...');
    const { error: deleteError, count: deletedCount } = await supabase
      .from('directories')
      .delete()
      .neq('id', '00000000-0000-0000-0000-000000000000'); // Delete all records

    if (deleteError) {
      console.error('Error deleting records:', deleteError);
      throw deleteError;
    }
    console.log(`Deleted existing records`);

    // Insert new records in batches (Supabase has a limit)
    const batchSize = 100;
    let successCount = 0;
    let errorCount = 0;

    console.log('\nInserting new records...');
    for (let i = 0; i < records.length; i += batchSize) {
      const batch = records.slice(i, i + batchSize);
      console.log(`Inserting batch ${Math.floor(i / batchSize) + 1}/${Math.ceil(records.length / batchSize)} (${batch.length} records)...`);

      const { data, error } = await supabase
        .from('directories')
        .insert(batch);

      if (error) {
        console.error(`Error inserting batch ${Math.floor(i / batchSize) + 1}:`, error);
        errorCount += batch.length;
      } else {
        successCount += batch.length;
        console.log(`✓ Batch ${Math.floor(i / batchSize) + 1} inserted successfully`);
      }
    }

    console.log('\n=== SYNC COMPLETE ===');
    console.log(`Successfully inserted: ${successCount} records`);
    console.log(`Errors: ${errorCount} records`);

    // Verify count
    const { count, error: countError } = await supabase
      .from('directories')
      .select('*', { count: 'exact', head: true });

    if (!countError) {
      console.log(`\nTotal records in directories table: ${count}`);
    }

  } catch (error) {
    console.error('Fatal error:', error);
    process.exit(1);
  }
}

// Run the sync
syncDirectories();
