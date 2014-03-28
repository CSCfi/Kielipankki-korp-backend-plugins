#! /usr/bin/python
# -*- coding: utf-8 -*-


from __future__ import absolute_import

from .exporter import KorpExporter


__all__ = ['KorpExporterCSV', 'KorpExporterTSV']


class KorpExporterDelimited(KorpExporter):

    _option_defaults = {}
    _delimit_opts = {"delimiter": u",",
                     "quote": u"\"",
                     "replace_quote": u"\"\"",
                     "newline": u"\n"}

    def __init__(self, *args, **kwargs):
        KorpExporter.__init__(self, *args, **kwargs)

    def format_headings(self):
        return self.format_fields(
            ["corpus", "position", "left context", "match", "right context"]
            + (["aligned text"] if self.is_parallel_corpus() else [])
            + self._opts.get("structs", []))

    def format_sentence(self, sentence):
        """Format a single delimited sentence.

        The result contains the following fields:
        - corpus ID (in upper case)
        - corpus position of the start of the match
        - tokens in left context, separated with spaces
        - tokens in match, separated with spaces
        - tokens in right context, separated with spaces
        - for parallel corpora only: tokens in aligned sentence
        """
        fields = ([self.get_sentence_corpus(sentence),
                   str(self.get_sentence_match_position(sentence))]
                  + [self.format_tokens(field_get_method(sentence))
                     for field_get_method in
                     [self.get_sentence_tokens_left_context,
                      self.get_sentence_tokens_match,
                      self.get_sentence_tokens_right_context]])
        for _, tokens in self.get_aligned_sentences(sentence):
            fields.append(self.format_tokens(tokens))
        fields.extend(self.get_sentence_struct_values(sentence))
        return self.format_fields(fields)

    def format_fields(self, fields):
        """Format fields according to the options in self._delimit_opts.

        self._delimit_opts may contain the following keyword arguments:
        - delim: field delimiter (default: ,)
        - quote: quotes surrounding fields (default: ")
        - replace_quote: string to replace a quote with in a field value to
          escape it (default: "")
        - newline: end-of-record string (default: \r\n)
        """
        delim = self._delimit_opts["delimiter"]
        quote = self._delimit_opts["quote"]
        replace_quote = self._delimit_opts["replace_quote"]
        newline = self._delimit_opts["newline"]
        return (delim.join((quote + field.replace(quote, replace_quote) + quote)
                           for field in fields)
                + newline)


class KorpExporterCSV(KorpExporterDelimited):

    _formats = ["csv"]
    _mime_type = "text/csv"
    _filename_extension = ".csv"
    _delimit_opts = {"delimiter": u",",
                     "quote": u"\"",
                     "replace_quote": u"\"\"",
                     "newline": u"\r\n"}

    def __init__(self, *args, **kwargs):
        KorpExporterDelimited.__init__(self, *args, **kwargs)


class KorpExporterTSV(KorpExporterDelimited):

    _formats = ["tsv"]
    _mime_type = "text/tsv"
    _filename_extension = ".tsv"
    _delimit_opts = {"delimiter": u"\t",
                     "quote": u"",
                     "replace_quote": u"",
                     "newline": u"\r\n"}

    def __init__(self, *args, **kwargs):
        KorpExporterDelimited.__init__(self, *args, **kwargs)
