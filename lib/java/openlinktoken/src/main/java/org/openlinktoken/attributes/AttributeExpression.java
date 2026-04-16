/* SPDX-License-Identifier: MIT */

package org.openlinktoken.attributes;

import java.io.Serializable;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.regex.PatternSyntaxException;

import org.apache.commons.lang3.time.DateUtils;

import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.Setter;

/**
 * An attribute expression determines how the value of an
 * attribute is normalized for consumption.
 *
 * <p>
 * Below are the components used to compose the attribute expression:
 *
 * <ul>
 * <li><code>T</code> - trim</li>
 * <li><code>U</code> - convert to upper case</li>
 * <li><code>S(start_index, end_index)</code> - substring of value</li>
 * <li><code>D</code> - treat as date</li>
 * <li><code>M(regex)</code> - match the regular expression</li>
 * <li><code>|</code> - expression separator</li>
 * </ul>
 *
 * <p>
 * Examples of attribute expressions:
 * <ul>
 * <li><code>T|S(0,3)|U</code> - trim the value, then take first 3 characters,
 * and then convert to upper case.</li>
 * <li><code>T|D</code> - trim the value, treat the value as a date in the
 * yyyy-MM-dd format.</li>
 * <li><code>T|M("\\d+")</code> - trim the value, then make sure that the value
 * matches the regular expression.</li>
 * </ul>
 */
@AllArgsConstructor
@Getter
@Setter
public final class AttributeExpression implements Serializable {

    private static final long serialVersionUID = 1L;
    private static final Pattern EXPRESSION_PATTERN = Pattern
            .compile("\\s*(?<expr>[^ (]+)(?:\\((?<args>[^\\)]+)\\))?");

    private Class<? extends Attribute> attributeClass;
    private String expressions;

    /**
     * Get the effective value for an attribute after application
     * of the attribute expression.
     *
     * @param value the attribute value
     *
     * @return the effective value after applying the attribute expression
     */
    public String getEffectiveValue(String value) {

        if (value == null || value.isBlank()) {
            return "";
        }

        if (expressions == null || expressions.isBlank()) {
            return value;
        }

        String result = value;
        String[] expressionParts = expressions.split("\\|");
        for (String expression : expressionParts) {
            result = eval(result, expression);
        }
        return result;
    }

    private static IllegalArgumentException evalError(String value, String expression, Throwable innerException) {
        return new IllegalArgumentException(
                String.format("Unable to evaluate expression [%s] over value [%s].", expression, value),
                innerException);
    }

    private static String eval(String value, String expression) {
        if (value == null || expression == null) {
            throw evalError(value, expression, null);
        }

        Matcher matcher = EXPRESSION_PATTERN.matcher(expression);
        if (!matcher.matches()) {
            throw evalError(value, expression, null);
        }

        String expr = matcher.group("expr");
        String[] args = null;
        if (matcher.group("args") != null) {
            args = matcher.group("args").trim().split(",");
        }

        switch (Character.toUpperCase(expr.charAt(0))) {
            case 'U':
                return value.toUpperCase();
            case 'T':
                return value.trim();
            case 'S':
                if (args == null) {
                    throw evalError(value, expression, null);
                }
                return S(value, expression, args);
            case 'R':
                if (args == null) {
                    throw evalError(value, expression, null);
                }
                return R(value, expression, args);
            case 'M':
                if (args == null) {
                    throw evalError(value, expression, null);
                }
                return M(value, expression, args);
            case 'D':
                return D(value, expression);
            default:
                throw evalError(value, expression, null);
        }
    }

    // Substring expression S(start,count)
    private static String S(String value, String expression, String[] args) {

        if (args.length != 2) {
            throw evalError(value, expression, null);
        }

        int start;
        int end;
        try {
            start = Math.max(0, Integer.parseInt(args[0]));
            end = Math.min(value.length(), Integer.parseInt(args[1]));

            // Let Substring handle index out of range checks.
            return value.substring(start, end);
        } catch (IndexOutOfBoundsException ex) {
            throw evalError(value, expression, ex);
        }
    }

    // Replace expression R(oldString,newString)
    private static String R(String value, String expression, String[] args) {

        if (args.length != 2) {
            throw evalError(value, expression, null);
        }

        try {
            String oldVal = args[0].substring(1, args[0].length() - 1);
            String newVal = args[1].substring(1, args[1].length() - 1);

            // Let Replace validate null, empty, etc...
            return value.replace(oldVal, newVal);
        } catch (Exception ex) {
            throw evalError(value, expression, ex);
        }
    }

    // RegExe match M(regex)
    private static String M(String value, String expression, String[] args) {

        if (args.length != 1) {
            throw evalError(value, expression, null);
        }

        StringBuilder result = new StringBuilder();
        try {
            Pattern pattern = Pattern.compile(args[0]);
            Matcher matcher = pattern.matcher(value);

            while (matcher.find()) {
                result.append(matcher.group());
            }

            return result.toString();
        } catch (PatternSyntaxException ex) {
            throw evalError(value, expression, ex);
        }
    }

    // Date expression
    private static String D(String value, String expression) {
        // Supported date formats, and will be changed to "yyyy-MM-dd"
        // If the date is not in the supported formats, an exception will be thrown.
        String[] possibleFormats = {
                "yyyy-MM-dd"
        };
        try {
            Date date = DateUtils.parseDate(value, possibleFormats);
            SimpleDateFormat targetFormat = new SimpleDateFormat("yyyy-MM-dd");
            return targetFormat.format(date);
        } catch (ParseException ex) {
            throw evalError(value, expression, ex);
        }
    }

}
