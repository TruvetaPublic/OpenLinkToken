/**
 * Copyright (c) Truveta. All rights reserved.
 */

import { AttributeValidator } from './AttributeValidator';

/**
 * A validator that asserts that a date value is within a configurable date range.
 *
 * This validator can be configured with:
 * - Minimum date (inclusive) - can be null for no lower bound
 * - Maximum date (inclusive) - can be null for no upper bound
 * - Use current date as maximum - dynamically sets max to today
 */
export class DateRangeValidator implements AttributeValidator {
  // Supported formats (not used directly, but documented for reference)
  // private static readonly POSSIBLE_INPUT_FORMATS = [
  //   /^\d{4}-\d{2}-\d{2}$/,          // yyyy-MM-dd
  //   /^\d{4}\/\d{2}\/\d{2}$/,         // yyyy/MM/dd
  //   /^\d{2}\/\d{2}\/\d{4}$/,         // MM/dd/yyyy
  //   /^\d{2}-\d{2}-\d{4}$/,           // MM-dd-yyyy
  //   /^\d{2}\.\d{2}\.\d{4}$/,         // dd.MM.yyyy
  // ];

  private minDate: Date | null;
  private maxDate: Date | null;
  private useCurrentDateAsMax: boolean;

  /**
   * Creates a DateRangeValidator with specified minimum and maximum dates.
   *
   * @param minDate - The minimum allowed date (inclusive), or null for no lower bound
   * @param maxDate - The maximum allowed date (inclusive), or null for no upper bound
   * @param useCurrentDateAsMax - If true, uses current date as maximum
   */
  constructor(
    minDate: Date | null = null,
    maxDate: Date | null = null,
    useCurrentDateAsMax = false
  ) {
    this.minDate = minDate;
    this.maxDate = maxDate;
    this.useCurrentDateAsMax = useCurrentDateAsMax;
  }

  /**
   * Validates that the date value is within the configured range.
   *
   * @param value - The date string to validate
   * @returns true if the date is within the configured range, false otherwise
   */
  validate(value: string): boolean {
    if (!value || value.trim().length === 0) {
      return false;
    }

    const parsedDate = this.parseDate(value);
    if (!parsedDate) {
      return false;
    }

    // Check minimum date
    if (this.minDate && parsedDate < this.minDate) {
      return false;
    }

    // Check maximum date
    const effectiveMaxDate = this.useCurrentDateAsMax ? new Date() : this.maxDate;
    if (effectiveMaxDate) {
      // Set time to end of day for comparison
      const maxDateEndOfDay = new Date(effectiveMaxDate);
      maxDateEndOfDay.setHours(23, 59, 59, 999);
      if (parsedDate > maxDateEndOfDay) {
        return false;
      }
    }

    return true;
  }

  /**
   * Parses a date string in various supported formats.
   *
   * @param value - The date string to parse
   * @returns The parsed Date object, or null if parsing fails
   */
  private parseDate(value: string): Date | null {
    // Try yyyy-MM-dd
    if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
      const date = new Date(value);
      return isNaN(date.getTime()) ? null : date;
    }

    // Try yyyy/MM/dd
    if (/^\d{4}\/\d{2}\/\d{2}$/.test(value)) {
      const date = new Date(value.replace(/\//g, '-'));
      return isNaN(date.getTime()) ? null : date;
    }

    // Try MM/dd/yyyy
    if (/^\d{2}\/\d{2}\/\d{4}$/.test(value)) {
      const parts = value.split('/');
      const date = new Date(`${parts[2]}-${parts[0]}-${parts[1]}`);
      return isNaN(date.getTime()) ? null : date;
    }

    // Try MM-dd-yyyy
    if (/^\d{2}-\d{2}-\d{4}$/.test(value)) {
      const parts = value.split('-');
      const date = new Date(`${parts[2]}-${parts[0]}-${parts[1]}`);
      return isNaN(date.getTime()) ? null : date;
    }

    // Try dd.MM.yyyy
    if (/^\d{2}\.\d{2}\.\d{4}$/.test(value)) {
      const parts = value.split('.');
      const date = new Date(`${parts[2]}-${parts[1]}-${parts[0]}`);
      return isNaN(date.getTime()) ? null : date;
    }

    return null;
  }
}
