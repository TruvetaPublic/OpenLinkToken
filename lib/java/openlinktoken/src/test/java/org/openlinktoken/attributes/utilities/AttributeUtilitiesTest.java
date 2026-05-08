/* SPDX-License-Identifier: MIT */
package org.openlinktoken.attributes.utilities;

import static org.junit.jupiter.api.Assertions.assertEquals;
import org.junit.jupiter.api.Test;

class AttributeUtilitiesTest {

    @Test
    void normalizeDiacritics_ShouldTransliterateLatinExtendedCharacters() {
        String[][] cases = {
                { "Æ", "AE" },
                { "æ", "ae" },
                { "Ð", "D" },
                { "ð", "d" },
                { "Ø", "O" },
                { "ø", "o" },
                { "Þ", "TH" },
                { "þ", "th" },
                { "ß", "ss" },
                { "ẞ", "SS" },
                { "Đ", "D" },
                { "đ", "d" },
                { "Ħ", "H" },
                { "ħ", "h" },
                { "ı", "i" },
                { "Ĳ", "IJ" },
                { "ĳ", "ij" },
                { "Ŀ", "L" },
                { "ŀ", "l" },
                { "Ł", "L" },
                { "ł", "l" },
                { "ŉ", "n" },
                { "Ŋ", "NG" },
                { "ŋ", "ng" },
                { "Œ", "OE" },
                { "œ", "oe" },
                { "Ŧ", "T" },
                { "ŧ", "t" },
                { "ſ", "s" },
                { "Ƒ", "F" },
                { "ƒ", "f" },
                { "Ǆ", "DZ" },
                { "ǅ", "Dz" },
                { "ǆ", "dz" },
                { "Ǉ", "LJ" },
                { "ǈ", "Lj" },
                { "ǉ", "lj" },
                { "Ǌ", "NJ" },
                { "ǋ", "Nj" },
                { "ǌ", "nj" },
                { "Ǳ", "DZ" },
                { "ǲ", "Dz" },
                { "ǳ", "dz" },
                { "Ǽ", "AE" },
                { "ǽ", "ae" },
                { "Ǿ", "O" },
                { "ǿ", "o" }
        };

        for (String[] testCase : cases) {
            assertEquals(testCase[1], AttributeUtilities.normalizeDiacritics(testCase[0]), testCase[0]);
        }
    }

    @Test
    void normalizeDiacritics_ShouldHandleRealNameExamples() {
        String[][] cases = {
                { "Łukasz", "Lukasz" },
                { "Søren Kierkegård", "Soren Kierkegard" },
                { "Ægir Þór", "AEgir THor" },
                { "Đỗ", "Do" },
                { "Dvořák⃝", "Dvorak" }
        };

        for (String[] testCase : cases) {
            assertEquals(testCase[1], AttributeUtilities.normalizeDiacritics(testCase[0]), testCase[0]);
        }
    }
}
