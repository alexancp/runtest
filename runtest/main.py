

def check(filter_list, out_name, ref_name, verbose=False):
    """
    Compares output (work_dir/out_name) with reference (work_dir/ref_name)
    applying all filters tasks from the list of filters.

    Input:
        - work_dir -- working directory
        - out_name -- actual output file name
        - ref_name -- reference output file name
        - verbose  -- give verbose output upon failure

    Returns:
        - nothing

    Generates the following files in work_dir:
        - out_name.filtered  -- numbers extracted from output
        - out_name.reference -- numbers extracted from reference
        - out_name.diff      -- difference between the two above

    Raises:
        - TestFailedError
    """
    import os
    from .tuple_comparison import tuple_matches
    from .extract import extract_numbers
    from .scissors import cut_sections
    from .exceptions import FilterKeywordError, TestFailedError, BadFilterError

    def _tuple_matches(t):
        if f.tolerance_is_relative:
            error_definition = 'relative'
        else:
            error_definition = 'absolute'
        return tuple_matches(t,
                             tolerance=f.tolerance,
                             error_definition=error_definition,
                             ignore_sign=f.ignore_sign,
                             skip_below=f.ignore_below,
                             skip_above=f.ignore_above)

    log_out = open('%s.filtered' % out_name, 'w')
    log_ref = open('%s.reference' % out_name, 'w')
    log_diff = open('%s.diff' % out_name, 'w')

    for f in filter_list:

        out_filtered = cut_sections(open(out_name).readlines(),
                                    from_string=f.from_string,
                                    from_is_re=f.from_is_re,
                                    to_string=f.to_string,
                                    to_is_re=f.to_is_re,
                                    num_lines=f.num_lines)
        if out_filtered == []:
            if f.num_lines > 0:
                r = '[%i lines from "%s"]' % (f.num_lines, f.from_string)
            else:
                r = '["%s" ... "%s"]' % (f.from_string, f.to_string)
            message = 'ERROR: filter %s did not extract anything from file %s\n' % (r, out_name)
            raise BadFilterError(message)

        log_out.write(''.join(out_filtered))
        out_numbers, out_locations = extract_numbers(out_filtered, f.mask)
        if f.mask is not None and out_numbers == []:
            raise FilterKeywordError('ERROR: mask %s did not extract any numbers\n' % f.mask)

        ref_filtered = cut_sections(open(ref_name).readlines(),
                                    from_string=f.from_string,
                                    from_is_re=f.from_is_re,
                                    to_string=f.to_string,
                                    to_is_re=f.to_is_re,
                                    num_lines=f.num_lines)
        if ref_filtered == []:
            if f.num_lines > 0:
                r = '[%i lines from "%s"]' % (f.num_lines, f.from_string)
            else:
                r = '["%s" ... "%s"]' % (f.from_string, f.to_string)
            message = 'ERROR: filter %s did not extract anything from file %s\n' % (r, ref_name)
            raise BadFilterError(message)

        log_ref.write(''.join(ref_filtered))
        ref_numbers, _ = extract_numbers(ref_filtered, f.mask)
        if f.mask is not None and ref_numbers == []:
            raise FilterKeywordError('ERROR: mask %s did not extract any numbers\n' % f.mask)

        if out_numbers == [] and ref_numbers == []:
            # no numbers are extracted
            if out_filtered != ref_filtered:
                log_diff.write('ERROR: extracted strings do not match\n')
                log_diff.write('own gave:\n')
                log_diff.write(''.join(out_filtered) + '\n')
                log_diff.write('reference gave:\n')
                log_diff.write(''.join(ref_filtered) + '\n')

        # we need to check for len(out_numbers) > 0
        # for pure strings len(out_numbers) is 0
        # TODO need to consider what to do with pure strings in future versions
        if len(out_numbers) == len(ref_numbers) and len(out_numbers) > 0:
            if not f.tolerance_is_set and (any(map(lambda x: isinstance(x, float), out_numbers)) or any(map(lambda x: isinstance(x, float), ref_numbers))):
                raise FilterKeywordError('ERROR: for floats you have to specify either rel_tolerance or abs_tolerance\n')
            l = map(_tuple_matches, zip(out_numbers, ref_numbers))
            matching, errors = zip(*l)  # unzip tuples to two lists
            if not all(matching):
                log_diff.write('\n')
                for k, line in enumerate(out_filtered):
                    log_diff.write('.       %s' % line)
                    for i, num in enumerate(out_numbers):
                        (line_num, start_char, length) = out_locations[i]
                        if line_num == k:
                            if errors[i]:
                                log_diff.write('ERROR   %s%s %s\n' % (' ' * start_char, '#' * length, errors[i]))

        if len(out_numbers) != len(ref_numbers):
            log_diff.write('ERROR: extracted sizes do not match\n')
            log_diff.write('own gave %i numbers:\n' % len(out_numbers))
            log_diff.write(''.join(out_filtered) + '\n')
            log_diff.write('reference gave %i numbers:\n' % len(ref_numbers))
            log_diff.write(''.join(ref_filtered) + '\n')

    log_out.close()
    log_ref.close()
    log_diff.close()

    if os.path.getsize('%s.diff' % out_name) > 0:
        log_diff = open('%s.diff' % out_name, 'r')
        diff = ''
        for line in log_diff.readlines():
            diff += line
        log_diff.close()
        message = "ERROR: test %s failed\n" % out_name
        if verbose:
            message += diff
        raise TestFailedError(message)
