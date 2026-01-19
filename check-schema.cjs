const { createClient } = require('@supabase/supabase-js');

const SUPABASE_URL = 'https://kolgqfjgncdwddziqloz.supabase.co';
const SUPABASE_SERVICE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtvbGdxZmpnbmNkd2RkemlxbG96Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NjczODc2MSwiZXhwIjoyMDcyMzE0NzYxfQ.xPoR2Q_yey7AQcorPG3iBLKTadzzSEMmK3eM9ZW46Qc';

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);

async function checkSchema() {
  // Get a sample row to see the structure
  const { data, error } = await supabase
    .from('directories')
    .select('*')
    .limit(1);

  if (error) {
    console.error('Error:', error);
  } else {
    console.log('Sample row:', JSON.stringify(data, null, 2));
  }

  // Query PostgreSQL system tables to get enum values for submission_method
  const { data: enumData, error: enumError } = await supabase
    .rpc('get_enum_values', { enum_name: 'submission_method' })
    .single();

  if (enumError) {
    console.log('Could not get enum values via RPC:', enumError.message);
  } else {
    console.log('Enum values:', enumData);
  }
}

checkSchema();
