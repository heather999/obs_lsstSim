#!/usr/bin/env python

# 
# LSST Data Management System
# Copyright 2008, 2009, 2010 LSST Corporation.
# 
# This product includes software developed by the
# LSST Project (http://www.lsst.org/).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the LSST License Statement and 
# the GNU General Public License along with this program.  If not, 
# see <http://www.lsstcorp.org/LegalNotices/>.
#

"""Test lsst.obs.lsstSim.ScaleLsstSimZeroPointTask
"""
import numpy
import unittest

import lsst.daf.base
import lsst.afw.geom as afwGeom
import lsst.afw.image as afwImage
import lsst.afw.math as afwMath

import lsst.utils.tests as utilsTests
from lsst.daf.persistence import DbAuth
from lsst.obs.lsstSim.scaleLsstSimZeroPoint import ScaleLsstSimZeroPointTask

    
#-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-

class ScaleLsstSimZeroPointTaskTestCase(unittest.TestCase):
    """A test case for ScaleLsstSimZeroPointTask
    """
    def makeTestExposure(self, xNumPix, yNumPix):
        """
        Create and return an exposure that is completely covered by the database: test_select_lsst_images
        """
        metadata = lsst.daf.base.PropertySet()
        metadata.set("NAXIS", 2)
        metadata.set("RADECSYS", "ICRS")
        metadata.set("EQUINOX", 2000.)
        metadata.setDouble("CRVAL1", 60.000000000000)
        metadata.setDouble("CRVAL2", 10.812316963572)
        metadata.setDouble("CRPIX1", 700000.00000000)
        metadata.setDouble("CRPIX2", 601345.00000000)
        metadata.set("CTYPE1", "RA---STG")
        metadata.set("CTYPE2", "DEC--STG")
        metadata.setDouble("CD1_1", -5.5555555555556e-05)
        metadata.setDouble("CD1_2", 0.0000000000000)
        metadata.setDouble("CD2_2", 5.5555555555556e-05)
        metadata.setDouble("CD2_1", 0.0000000000000)
        metadata.set("CUNIT1", "deg")
        metadata.set("CUNIT2", "deg")
        #exposure needs a wcs and a bbox
        wcs = afwImage.makeWcs(metadata)
        bbox = afwGeom.Box2I(afwGeom.Point2I(327750, 235750), afwGeom.Extent2I(xNumPix, yNumPix))
        exposure = afwImage.ExposureF(bbox, wcs)
        mi = exposure.getMaskedImage()
        mi.set(1.0)
        mi.getVariance().set(1.0)        
        return exposure
    
    def testBasics(self):
        ZEROPOINT = 27
        self.sctrl = afwMath.StatisticsControl()
        self.sctrl.setNanSafe(True)        
        config = ScaleLsstSimZeroPointTask.ConfigClass()
        config.zeroPoint = ZEROPOINT
        config.interpStyle = "CONSTANT"
        config.selectFluxMag0.database = "test_select_lsst_images"
        zpScaler = ScaleLsstSimZeroPointTask(config=config)
        outCalib = zpScaler.getCalib()
        self.assertAlmostEqual(outCalib.getMagnitude(1.0), ZEROPOINT)
        
        exposure = self.makeTestExposure(10,10)
        exposureId = {'ignore_fake_key': 1234, 'visit': 882820621}

        #test methods: computeImageScale(), scaleMaskedImage(), getInterpImage()
        imageScaler = zpScaler.computeImageScaler(exposure,exposureId)
        scaleFactorIm = imageScaler.getInterpImage(exposure.getBBox())
        predScale = numpy.mean(imageScaler._scaleList) #0.011125492863357
        
        self.assertAlmostEqual(afwMath.makeStatistics(scaleFactorIm, afwMath.VARIANCE, self.sctrl).getValue(),
                               0.0)
        self.assertAlmostEqual(afwMath.makeStatistics(scaleFactorIm, afwMath.MEAN, self.sctrl).getValue(),
                               predScale)

        mi = exposure.getMaskedImage()
        imageScaler.scaleMaskedImage(mi)
        self.assertAlmostEqual(mi.get(1,1)[0], predScale) #check image plane scaled
        self.assertAlmostEqual(mi.get(1,1)[2], predScale**2) #check variance plane scaled

        exposure.setCalib(zpScaler.getCalib())    
        self.assertAlmostEqual(exposure.getCalib().getFlux(ZEROPOINT), 1.0)

                                
    def makeCalib(self, zeroPoint):
        calib = afwImage.Calib()
        fluxMag0 = 10**(0.4 * zeroPoint)
        calib.setFluxMag0(fluxMag0, 1.0)
        return calib


def suite():
    """Return a suite containing all the test cases in this module.
    """
    utilsTests.init()

    suites = [
        unittest.makeSuite(ScaleLsstSimZeroPointTaskTestCase),
        unittest.makeSuite(utilsTests.MemoryTestCase),
    ]

    return unittest.TestSuite(suites)


def run(shouldExit=False):
    """Run the tests"""
    config =  ScaleLsstSimZeroPointTask.ConfigClass()
    try:
        user = DbAuth.username(config.selectFluxMag0.host, str(config.selectFluxMag0.port)),
    except Exception, e:
        print "Warning: did not find host=%s, port=%s in your db-auth file; or %s " \
              "skipping SelectLsstImagesTask unit tests" % \
            (config.selectFluxMag0.host, str(config.selectFluxMag0.port), e)
        return

    utilsTests.run(suite(), shouldExit)


if __name__ == "__main__":
    run(True)
