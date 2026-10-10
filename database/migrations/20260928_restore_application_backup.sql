-- Apply manually in the Supabase SQL editor after reviewing the function.
-- Restores only the 14 application tables. BackupHistory is intentionally excluded.
-- The function runs as one PostgreSQL statement/transaction: any table failure rolls back all tables.
CREATE OR REPLACE FUNCTION public.restore_application_backup(p_backup jsonb)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = pg_catalog, public
AS $$
DECLARE
    item record;
    column_list text;
    select_list text;
    update_list text;
    restored_rows bigint;
    max_id bigint;
    sequence_name text;
    sequence_last bigint;
    sequence_called boolean;
    table_results jsonb := '[]'::jsonb;
BEGIN
    IF jsonb_typeof(p_backup) <> 'object' THEN
        RAISE EXCEPTION 'Backup must be a JSON object';
    END IF;

    FOR item IN
        SELECT * FROM (VALUES
            ('Roles', 'role_id'), ('Users', 'user_id'), ('Categories', 'category_id'),
            ('Products', 'product_id'), ('Suppliers', 'supplier_id'),
            ('SupplierQuotations', 'quotation_id'), ('PurchaseOrders', 'purchase_order_id'),
            ('PurchaseOrderItems', 'purchase_order_item_id'), ('Inventory', 'inventory_id'),
            ('StockTransactions', 'transaction_id'), ('Notifications', 'notification_id'),
            ('AuditLogs', 'log_id'), ('SystemStatus', 'status_id'), ('Reports', 'report_id')
        ) AS t(table_name, pk)
    LOOP
        IF jsonb_typeof(p_backup -> item.table_name) <> 'array' THEN
            RAISE EXCEPTION 'Backup table % must be an array', item.table_name;
        END IF;

        SELECT
            string_agg(format('%I', a.attname), ', ' ORDER BY a.attnum),
            string_agg(format('(r).%I', a.attname), ', ' ORDER BY a.attnum),
            string_agg(format('%I = EXCLUDED.%I', a.attname, a.attname), ', ' ORDER BY a.attnum)
                FILTER (WHERE a.attname <> item.pk)
        INTO column_list, select_list, update_list
        FROM pg_attribute a
        WHERE a.attrelid = format('public.%I', item.table_name)::regclass
          AND a.attnum > 0 AND NOT a.attisdropped
          AND a.attgenerated = '';

        IF column_list IS NULL OR position(format('%I', item.pk) IN column_list) = 0 THEN
            RAISE EXCEPTION 'Restore schema is unavailable for table %', item.table_name;
        END IF;

        IF jsonb_array_length(p_backup -> item.table_name) > 0 THEN
            IF update_list IS NULL THEN
                EXECUTE format(
                    'INSERT INTO public.%I (%s) OVERRIDING SYSTEM VALUE SELECT %s FROM jsonb_populate_recordset(NULL::public.%I, $1) AS r ON CONFLICT (%I) DO NOTHING',
                    item.table_name, column_list, select_list, item.table_name, item.pk
                ) USING p_backup -> item.table_name;
            ELSE
                EXECUTE format(
                    'INSERT INTO public.%I (%s) OVERRIDING SYSTEM VALUE SELECT %s FROM jsonb_populate_recordset(NULL::public.%I, $1) AS r ON CONFLICT (%I) DO UPDATE SET %s',
                    item.table_name, column_list, select_list, item.table_name, item.pk, update_list
                ) USING p_backup -> item.table_name;
            END IF;
            GET DIAGNOSTICS restored_rows = ROW_COUNT;
        ELSE
            restored_rows := 0;
        END IF;

        table_results := table_results || jsonb_build_array(jsonb_build_object(
            'table', item.table_name, 'primary_key', item.pk,
            'records_processed', jsonb_array_length(p_backup -> item.table_name),
            'rows_affected', restored_rows, 'status', 'Success'
        ));
    END LOOP;

    -- Move identity sequences forward only, after every table insert has succeeded.
    -- setval is not transactional in PostgreSQL, so no sequence is touched until all
    -- potentially failing restore writes have completed.
    FOR item IN
        SELECT * FROM (VALUES
            ('Roles', 'role_id'), ('Users', 'user_id'), ('Categories', 'category_id'),
            ('Products', 'product_id'), ('Suppliers', 'supplier_id'),
            ('SupplierQuotations', 'quotation_id'), ('PurchaseOrders', 'purchase_order_id'),
            ('PurchaseOrderItems', 'purchase_order_item_id'), ('Inventory', 'inventory_id'),
            ('StockTransactions', 'transaction_id'), ('Notifications', 'notification_id'),
            ('AuditLogs', 'log_id'), ('SystemStatus', 'status_id'), ('Reports', 'report_id')
        ) AS t(table_name, pk)
    LOOP
        sequence_name := pg_get_serial_sequence(format('public.%I', item.table_name), item.pk);
        IF sequence_name IS NOT NULL THEN
            EXECUTE format('SELECT max(%I)::bigint FROM public.%I', item.pk, item.table_name) INTO max_id;
            EXECUTE format('SELECT last_value, is_called FROM %s', sequence_name::regclass)
                INTO sequence_last, sequence_called;
            IF max_id IS NOT NULL AND (max_id > sequence_last OR (NOT sequence_called AND max_id >= sequence_last)) THEN
                PERFORM setval(sequence_name::regclass, max_id, true);
            END IF;
        END IF;
    END LOOP;

    RETURN table_results;
END;
$$;

REVOKE ALL ON FUNCTION public.restore_application_backup(jsonb) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.restore_application_backup(jsonb) TO service_role;
