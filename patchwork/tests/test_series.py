# Patchwork - automated patch tracking system
# Copyright (C) 2014 Intel Corporation
#
# This file is part of the Patchwork package.
#
# Patchwork is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Patchwork is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Patchwork; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import os

from django.test import TestCase
from patchwork.models import Patch, Series, SeriesRevision, Project, \
                             SERIES_DEFAULT_NAME
from patchwork.tests.utils import read_mail
from patchwork.tests.utils import defaults, read_mail, TestSeries

from patchwork.bin.parsemail import parse_mail, build_references_list

class SeriesTest(TestCase):
    fixtures = ['default_states']

    def setUp(self):
        self.assertTrue(self.project is not None)
        self.project.save()

        # insert the mails. 'mails' is an optional field, for subclasses
        # that do have a list of on-disk emails.
        if hasattr(self, 'mails'):
            self.n_mails = len(self.mails)
            for filename in self.mails:
                mail = read_mail(os.path.join('series', filename))
                parse_mail(mail)

    def commonInsertionChecks(self):
        # subclasses are responsible for defining those variables
        self.assertTrue(self.n_patches is not None)
        self.assertTrue(self.root_msgid is not None)
        self.assertTrue(self.series_name is not None)

        # make sure the series has been correctly populated
        series = Series.objects.all()
        self.assertEquals(series.count(), 1)

        s = series[0]
        self.assertEquals(s.project, self.project)
        self.assertEquals(s.name, self.series_name)

        # same thing for the revision
        revisions = SeriesRevision.objects.all()
        self.assertEquals(revisions.count(), 1)

        r = revisions[0]
        self.assertEquals(r.series_id, s.id)
        self.assertEquals(r.root_msgid, self.root_msgid)
        self.assertEquals(r.cover_letter, self.cover_letter)

        # and list of patches
        r_patches = r.patches.all()
        self.assertEquals(r_patches.count(), self.n_patches)

        # Make sure we also insert patches. Most thorough checks on patches
        # isn't the subject here.
        patches = Patch.objects.all()
        self.assertEquals(patches.count(), self.n_patches)

class GeneratedSeriesTest(SeriesTest):
    project = defaults.project

    def _create_series(self, n_patches, has_cover_letter=True):
        self.n_patches = n_patches
        series = TestSeries(self.n_patches, has_cover_letter)
        mails = series.create_mails()
        self.root_msgid = mails[0].get('Message-Id')
        self.has_cover_letter = has_cover_letter
        if has_cover_letter:
            self.series_name = defaults.series_name
            self.cover_letter = defaults.series_cover_letter
        else:
            self.series_name = SERIES_DEFAULT_NAME
            self.cover_letter = None
        return (series, mails)

class BasicGeneratedSeriesTests(GeneratedSeriesTest):
    def testInsertion(self):
        (series, mails) = self._create_series(3)
        series.insert(mails)
        self.commonInsertionChecks()

    def testInsertionNoCoverLetter(self):
        (series, mails) = self._create_series(3, has_cover_letter=False)
        series.insert(mails)
        self.commonInsertionChecks()

class IntelGfxTest(SeriesTest):
    project = Project(linkname = 'intel-gfx',
                      name = 'Intel Gfx',
                      listid = 'intel-gfx.lists.freedesktop.org',
                      listemail='intel-gfx@lists.freedesktop.org')

class SingleMailSeries(IntelGfxTest):
    mails = (
        '0001-single-mail.mbox',
    )
    n_patches = 1
    series_name = "drm/i915: Hold CRTC lock whilst freezing the planes"

    root_msgid = '<1400748280-26449-1-git-send-email-chris@chris-wilson.co.uk>'
    cover_letter = None

    def testInsertion(self):
        """A single patch is a series of 1 patch"""

        self.commonInsertionChecks()

        # make sure we got the right patch inserted as well
        patches = Patch.objects.all()
        patch = patches[0]
        self.assertEquals(patch.msgid, self.root_msgid)

class Series0010(IntelGfxTest):
    mails = (
        '0010-multiple-mails-cover-letter.mbox',
        '0011-multiple-mails-cover-letter.mbox',
        '0012-multiple-mails-cover-letter.mbox',
        '0013-multiple-mails-cover-letter.mbox',
        '0014-multiple-mails-cover-letter.mbox',
    )
    n_patches = 4
    series_name = "for_each_{intel_,}crtc v2"

    root_msgid = '<1400020344-17248-1-git-send-email-damien.lespiau@intel.com>'

    cover_letter = \
"""With Daniel's help to figure out an arcane corner of coccinelle, here is v2 of
a series introducing macros to iterate through the CRTCs instead of using
list_for_each_entry() and mode_config.crtc_list, a tiny bit more readable and
easier to recall.

Damien Lespiau (4):
  drm/i915: Introduce a for_each_intel_crtc() macro
  drm/i915: Use for_each_intel_crtc() when iterating through intel_crtcs
  drm/i915: Introduce a for_each_crtc() macro
  drm/i915: Use for_each_crtc() when iterating through the CRTCs

 drivers/gpu/drm/i915/i915_debugfs.c  |  4 +-
 drivers/gpu/drm/i915/i915_drv.c      |  2 +-
 drivers/gpu/drm/i915/i915_drv.h      |  6 +++
 drivers/gpu/drm/i915/intel_display.c | 71 +++++++++++++++---------------------
 drivers/gpu/drm/i915/intel_fbdev.c   |  6 +--
 drivers/gpu/drm/i915/intel_pm.c      | 12 +++---
 6 files changed, 47 insertions(+), 54 deletions(-)"""

class MultipleMailCoverLetterSeries(Series0010):
    def testInsertion(self):
        """A series with a cover letter and 4 patches"""

        self.commonInsertionChecks()

class MultipleMailCoverLetterSeriesUnordered(Series0010):
    mails = (
        '0013-multiple-mails-cover-letter.mbox',
        '0012-multiple-mails-cover-letter.mbox',
        '0010-multiple-mails-cover-letter.mbox',
        '0011-multiple-mails-cover-letter.mbox',
        '0014-multiple-mails-cover-letter.mbox',
    )

    def testInsertion(self):
        """A series with a cover letter and 4 patches, receiving emails in
           a different order than the 'natural' one, ie not starting by
           the cover letter"""

        self.commonInsertionChecks()

class Series0020(IntelGfxTest):
    mails = (
        '0020-multiple-mails-no-cover-letter.mbox',
        '0021-multiple-mails-no-cover-letter.mbox',
        '0022-multiple-mails-no-cover-letter.mbox',
    )
    n_patches = 3
    series_name = SERIES_DEFAULT_NAME

    root_msgid = '<1421182013-751-1-git-send-email-kenneth@whitecape.org>'
    cover_letter = None

class MultipleMailNoCoverLetterSeries(Series0020):
    def testInsertion(self):
        """A series with 3 patches, but no cover letter"""

        self.commonInsertionChecks()

class ReferencesListTest(TestCase):
    fixtures = ['default_states']

    def testSingleMail(self):
        series = TestSeries(1, has_cover_letter=False)
        mails = series.create_mails()
        refs = build_references_list(mails[0])
        self.assertEquals(refs, [])

    def testThread2Mails(self):
        series = TestSeries(1)
        mails = series.create_mails()
        refs = build_references_list(mails[1])
        self.assertEquals(len(refs), 1)
        self.assertEquals(refs[0], mails[0].get('Message-Id'))

    def setMessageId(self, mail, msgid):
        del mail['Message-Id']
        mail['Message-Id'] = msgid

    def testPartialReferences(self):
        """Tests using the db to get the full list of references, for emails
        that only have partial list of ancestors in their References header"""
        series = TestSeries(3)
        mails = series.create_mails()
        self.setMessageId(mails[1], 'patch_1_3_v1')
        self.setMessageId(mails[2], 'patch_2_3_v1')
        self.setMessageId(mails[3], 'patch_3_3_v1')
        # review of patch 2/3
        reply_1 = series.create_reply(mails[2])
        mails.append(reply_1)
        self.setMessageId(reply_1, 'reply_1')
        # reply to the review
        reply_2 = series.create_reply(reply_1)
        mails.append(reply_2)
        self.setMessageId(reply_2, 'reply_2')
        # let's add yet another reply
        reply_3 = series.create_reply(reply_2)
        mails.append(reply_3)
        self.setMessageId(reply_3, 'reply_3')
        # now a revised patch (v2), which won't have the whole reference chain
        patch_v2 = series.create_patch(2, in_reply_to=reply_3,
                                       subject_prefix="PATCH v2")
        mails.append(patch_v2)
        self.setMessageId(patch_v2, 'patch_2_3_v2')
        # for good measure, a reply to that new patch
        reply_4 = series.create_reply(patch_v2)
        mails.append(reply_4)
        self.setMessageId(reply_4, 'reply_4')

        series.insert(mails)

        # and now the v3 of that patch, we'll need to reconstruct the full
        # list of references
        patch_v3 = series.create_patch(2, in_reply_to=reply_4,
                                       subject_prefix="PATCH v3")
        self.setMessageId(patch_v3, 'patch_2_3_v3')
        self.assertEquals(build_references_list(patch_v3),
                          [reply_4.get('Message-Id'),
                           patch_v2.get('Message-Id'),
                           reply_3.get('Message-Id'),
                           reply_2.get('Message-Id'),
                           reply_1.get('Message-Id'),
                           mails[2].get('Message-Id'),
                           mails[0].get('Message-Id')])

#
# New version of a single patch
#
class Series0030(IntelGfxTest):
    mails = (
        '0030-patch-v2-in-reply.mbox',
        '0031-patch-v2-in-reply.mbox',
        '0032-patch-v2-in-reply.mbox',
        '0033-patch-v2-in-reply.mbox',
    )
    n_patches = 2
    root_msgid = '<1427726038-19718-1-git-send-email-deepak.s@linux.intel.com>'
    series_name = 'drm/i915: Clean-up idr table if context create fails.'

class UpdatedPatchTest(Series0030):
    def testNewRevision(self):
        series = Series.objects.all()[0]
        self.assertEquals(series.version, 2)

        revisions = SeriesRevision.objects.all()
        self.assertEquals(revisions.count(), 2)

        r = revisions[0]
        self.assertEquals(r.series_id, series.id)
        self.assertEquals(r.root_msgid, self.root_msgid)
        self.assertEquals(r.patches.count(), 1)
        p = r.patches.all()[0]
        self.assertEquals(p.msgid, self.root_msgid)

        r = revisions[1]
        self.assertEquals(r.series_id, series.id)
        self.assertEquals(r.root_msgid, self.root_msgid)
        self.assertEquals(r.patches.count(), 1)
        p = r.patches.all()[0]
        self.assertEquals(p.msgid,
                '<1427980954-15015-1-git-send-email-deepak.s@linux.intel.com>')

class SinglePatchUpdateTest(GeneratedSeriesTest):
    def check_revision(self, series, revision):
        self.assertEquals(revision.series_id, series.id)
        self.assertEquals(revision.root_msgid, self.root_msgid)
        self.assertEquals(revision.patches.count(), self.n_patches)

    def check(self, original_mails, patch_v2_mail, n):
        self.assertEquals(Series.objects.count(), 1)
        series = Series.objects.all()[0]
        self.assertEquals(series.version, 2)

        revisions = SeriesRevision.objects.all()
        self.assertEquals(revisions.count(), 2)

        r = revisions[0]
        self.check_revision(series, r)
        p = r.ordered_patches()[n - 1]
        if self.has_cover_letter:
            patch_mail = original_mails[n]
        else:
            patch_mail = original_mails[n - 1]
        self.assertEquals(p.msgid, patch_mail.get('Message-Id'))

        r = revisions[1]
        self.check_revision(series, r)
        self.assertTrue(r.cover_letter is None)
        p = r.ordered_patches()[n - 1]
        self.assertEquals(p.msgid, patch_v2_mail.get('Message-Id'))

    def _test_internal(self, n_patches, n_updated, has_cover_letter=True):
        (test, mails) = self._create_series(n_patches, has_cover_letter)
        test.insert(mails)
        self.commonInsertionChecks()
        i = n_updated - 1
        if has_cover_letter:
            i += 1
        new_patch = test.create_patch(n_updated, mails[i],
                                      subject_prefix='PATCH v2')
        test.insert((new_patch, ))

        self.check(mails, new_patch, n_updated)

    def testCoverLetterUpdateLen1Patch1(self):
        self._test_internal(1, 1, has_cover_letter=True)

    def testNoCoverLetterUpdateLen1Patch1(self):
        self._test_internal(1, 1, has_cover_letter=False)

    def testCoverLetterUpdateLen2Patch1(self):
        self._test_internal(2, 1, has_cover_letter=True)

    def testCoverLetterUpdateLen2Patch2(self):
        self._test_internal(2, 2, has_cover_letter=True)

    def testNoCoverLetterUpdateLen2Patch1(self):
        self._test_internal(2, 1, has_cover_letter=False)

    def testNoCoverLetterUpdateLen2Patch2(self):
        self._test_internal(2, 2, has_cover_letter=False)

    def testCoverLetterUpdateLen3Patch1(self):
        self._test_internal(3, 1, has_cover_letter=True)

    def testCoverLetterUpdateLen3Patch2(self):
        self._test_internal(3, 2, has_cover_letter=True)

    def testCoverLetterUpdateLen3Patch3(self):
        self._test_internal(3, 3, has_cover_letter=True)

    def testNoCoverLetterUpdateLen3Patch1(self):
        self._test_internal(3, 1, has_cover_letter=False)

    def testNoCoverLetterUpdateLen3Patch2(self):
        self._test_internal(3, 2, has_cover_letter=False)

    def testNoCoverLetterUpdateLen3Patch3(self):
        self._test_internal(3, 3, has_cover_letter=False)

class SinglePatchUpdatesVariousCornerCasesTest(TestCase):
    fixtures = ['default_states']

    def testSinglePatchUpdatesNotSerialized(self):
        """ + patch v1
            +--> patch v2
            +--> patch v3
        """
        mails = []
        dummy = TestSeries(1)
        patch_v1 = dummy.create_patch()
        mails.append(patch_v1)
        patch_v2 = dummy.create_patch(in_reply_to=mails[0],
                                      subject_prefix="PATCH v2")
        mails.append(patch_v2)
        patch_v3 = dummy.create_patch(in_reply_to=mails[0],
                                      subject_prefix="PATCH v3")
        mails.append(patch_v3)
        dummy.insert(mails)

        self.assertEquals(Series.objects.count(), 1)
        series = Series.objects.all()[0]
        self.assertEquals(series.version, 3)

        revisions = SeriesRevision.objects.all()
        self.assertEquals(revisions.count(), 3)

        revision = revisions[0]
        patches = revision.ordered_patches()
        self.assertEqual(len(patches), 1)
        self.assertEqual(patches[0].name, defaults.patch_name)

        revision = revisions[1]
        patches = revision.ordered_patches()
        self.assertEqual(len(patches), 1)
        self.assertEqual(patches[0].name, '[v2] ' + defaults.patch_name)

        revision = revisions[2]
        patches = revision.ordered_patches()
        self.assertEqual(len(patches), 1)
        self.assertEqual(patches[0].name, '[v3] ' + defaults.patch_name)

    def testSinglePatchUpdateNoCoverLetterNoSeriesMarker(self):
        """ + patch 1/2
             +--+ patch 2/2
                +--> patch v2 (but no 2/2)
        """
        series = TestSeries(2, has_cover_letter=False)
        mails = series.create_mails()

        patch_2_2_v2 = series.create_patch(in_reply_to=mails[1])
        del patch_2_2_v2['Subject']
        patch_2_2_v2['Subject'] = '[v2] ' + defaults.patch_name
        mails.append(patch_2_2_v2)

        series.insert(mails)

        self.assertEquals(Series.objects.count(), 1)
        series = Series.objects.all()[0]
        self.assertEquals(series.version, 2)

        revisions = SeriesRevision.objects.all()
        self.assertEquals(revisions.count(), 2)

        revision = revisions[0]
        patches = revision.ordered_patches()
        self.assertEqual(len(patches), 2)
        self.assertEqual(patches[0].name, '[1/2] ' + defaults.patch_name)
        self.assertEqual(patches[1].name, '[2/2] ' + defaults.patch_name)

        revision = revisions[1]
        patches = revision.ordered_patches()
        self.assertEqual(len(patches), 2)
        self.assertEqual(patches[0].name, '[1/2] ' + defaults.patch_name)
        self.assertEqual(patches[1].name, '[v2] ' + defaults.patch_name)
